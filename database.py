import sqlite3
import json
import logging
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class GameDatabase:
    """Класс для работы с базой данных игры"""

    def __init__(self, db_path: str = None):
        # Определяем путь к БД
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.db_path = db_path or os.path.join(BASE_DIR, "game.db")
        self._ensure_data_dir()
        self.init_database()
        logger.info(f"📁 Database initialized: {self.db_path}")

    def _ensure_data_dir(self):
        """Создает директорию для данных если нужно"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row

        # Включаем внешние ключи
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def init_database(self):
        """Инициализация таблиц базы данных"""
        try:
            with self.get_connection() as conn:
                # === ОСНОВНАЯ ТАБЛИЦА ИГРОКОВ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        class_name TEXT,
                        level INTEGER DEFAULT 1,
                        experience INTEGER DEFAULT 0,
                        gold INTEGER DEFAULT 50,
                        fatigue REAL DEFAULT 100,
                        last_fatigue_update REAL,
                        artifact_slots INTEGER DEFAULT 1,
                        current_location TEXT DEFAULT 'class_selection',
                        current_city TEXT DEFAULT 'village_square',
                        last_location TEXT DEFAULT 'village_square',
                        camp_entry_time REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # === СТАТИСТИКИ ИГРОКА ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS player_stats (
                        user_id INTEGER PRIMARY KEY,
                        health INTEGER DEFAULT 100,
                        attack INTEGER DEFAULT 10,
                        defense INTEGER DEFAULT 5,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE
                    )
                """)

                # === ИНВЕНТАРЬ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        item_id TEXT NOT NULL,
                        quantity INTEGER DEFAULT 1,
                        equipped BOOLEAN DEFAULT FALSE,
                        acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, item_id)
                    )
                """)

                # === АКТИВНЫЕ КВЕСТЫ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_quests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        quest_id TEXT NOT NULL,
                        progress TEXT DEFAULT '{}',
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, quest_id)
                    )
                """)

                # === ЗАВЕРШЕННЫЕ КВЕСТЫ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS completed_quests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        quest_id TEXT NOT NULL,
                        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, quest_id)
                    )
                """)

                # === АКТИВНЫЕ ЭФФЕКТЫ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_effects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        effect_name TEXT NOT NULL,
                        effect_data TEXT DEFAULT '{}',
                        duration INTEGER DEFAULT 1,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE
                    )
                """)

                # === ПРОГРЕСС СЮЖЕТА ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS story_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        city TEXT NOT NULL,
                        scene_id TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, city)
                    )
                """)

                # === ОТКРЫТЫЕ ЛОКАЦИИ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS unlocked_locations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        location_id TEXT NOT NULL,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, location_id)
                    )
                """)

                # === ПОБЕЖДЕННЫЕ БОССЫ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS defeated_bosses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        boss_id TEXT NOT NULL,
                        defeated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, boss_id)
                    )
                """)

                # === СЧЕТЧИК УБИЙСТВ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS kill_counts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        enemy_id TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        last_killed TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, enemy_id)
                    )
                """)

                # === СПОСОБНОСТИ ===
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS player_abilities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        ability_name TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES players (user_id) ON DELETE CASCADE,
                        UNIQUE(user_id, ability_name)
                    )
                """)

                # === ИНДЕКСЫ ===
                conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_active_quests_user ON active_quests(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kill_counts_user ON kill_counts(user_id)")

            logger.info("✅ Database tables created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise

    # ==================== МЕТОДЫ ДЛЯ ИГРОКОВ ====================

    def create_player(self, user_id: int, username: str = None,
                     first_name: str = None, last_name: str = None):
        """Создает нового игрока"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO players
                (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))

            conn.execute("""
                INSERT OR IGNORE INTO player_stats (user_id, health, attack, defense)
                VALUES (?, 100, 10, 5)
            """, (user_id,))

            conn.execute("""
                INSERT OR IGNORE INTO unlocked_locations (user_id, location_id)
                VALUES (?, 'village_square')
            """, (user_id,))

    def get_player(self, user_id: int) -> Optional[Dict]:
        """Получает основные данные игрока"""
        with self.get_connection() as conn:
            player_row = conn.execute(
                "SELECT * FROM players WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if not player_row:
                return None

            return dict(player_row)

    def get_full_player_data(self, user_id: int) -> Optional[Dict]:
        """Получает ВСЕ данные игрока"""
        with self.get_connection() as conn:
            player = self.get_player(user_id)
            if not player:
                return None

            # Статистика
            stats_row = conn.execute(
                "SELECT health, attack, defense FROM player_stats WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if stats_row:
                player['stats'] = dict(stats_row)

            # Инвентарь
            inventory_rows = conn.execute("""
                SELECT item_id, quantity, equipped
                FROM inventory
                WHERE user_id = ? AND quantity > 0
            """, (user_id,)).fetchall()

            player['inventory'] = []
            player['equipped_items'] = []
            for row in inventory_rows:
                # Добавляем предмет quantity раз в инвентарь
                for _ in range(row['quantity']):
                    player['inventory'].append(row['item_id'])
                if row['equipped']:
                    player['equipped_items'].append(row['item_id'])

            # Квесты
            active_rows = conn.execute(
                "SELECT quest_id FROM active_quests WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['active_quests'] = [row['quest_id'] for row in active_rows]

            completed_rows = conn.execute(
                "SELECT quest_id FROM completed_quests WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['completed_quests'] = [row['quest_id'] for row in completed_rows]

            # Эффекты
            effects_rows = conn.execute("""
                SELECT effect_name, effect_data, duration
                FROM active_effects
                WHERE user_id = ?
            """, (user_id,)).fetchall()

            player['active_effects'] = []
            for row in effects_rows:
                effect = {
                    'name': row['effect_name'],
                    'stats': json.loads(row['effect_data']) if row['effect_data'] else {},
                    'duration': row['duration']
                }
                player['active_effects'].append(effect)

            # Сюжет
            story_rows = conn.execute(
                "SELECT city, scene_id FROM story_progress WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['story_progress'] = {row['city']: row['scene_id'] for row in story_rows}

            # Локации
            location_rows = conn.execute(
                "SELECT location_id FROM unlocked_locations WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['unlocked_locations'] = [row['location_id'] for row in location_rows]

            # Боссы
            boss_rows = conn.execute(
                "SELECT boss_id FROM defeated_bosses WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['defeated_bosses'] = [row['boss_id'] for row in boss_rows]

            # Убийства
            kill_rows = conn.execute(
                "SELECT enemy_id, count FROM kill_counts WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['kill_count'] = {row['enemy_id']: row['count'] for row in kill_rows}

            # Способности
            ability_rows = conn.execute(
                "SELECT ability_name FROM player_abilities WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            player['abilities'] = [row['ability_name'] for row in ability_rows]

            return player

    def update_player(self, user_id: int, **kwargs):
        """Обновляет основные поля игрока"""
        if not kwargs:
            return

        with self.get_connection() as conn:
            fields = []
            values = []

            allowed_fields = ['class_name', 'level', 'experience', 'gold',
                             'fatigue', 'last_fatigue_update', 'artifact_slots',
                             'current_location', 'current_city', 'last_location',
                             'camp_entry_time']

            for key, value in kwargs.items():
                if key in allowed_fields:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if fields:
                values.append(user_id)
                query = f"UPDATE players SET {', '.join(fields)}, last_active = CURRENT_TIMESTAMP WHERE user_id = ?"
                conn.execute(query, values)

    def update_player_stats(self, user_id: int, health: int = None,
                           attack: int = None, defense: int = None):
        """Обновляет статистику игрока"""
        with self.get_connection() as conn:
            updates = []
            values = []

            if health is not None:
                updates.append("health = ?")
                values.append(health)
            if attack is not None:
                updates.append("attack = ?")
                values.append(attack)
            if defense is not None:
                updates.append("defense = ?")
                values.append(defense)

            if updates:
                values.append(user_id)
                query = f"UPDATE player_stats SET {', '.join(updates)} WHERE user_id = ?"
                conn.execute(query, values)

    # ==================== ИНВЕНТАРЬ ====================

    def add_item(self, user_id: int, item_id: str, quantity: int = 1):
        """Добавляет предмет в инвентарь"""
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            ).fetchone()

            if existing:
                new_quantity = existing['quantity'] + quantity
                conn.execute("""
                    UPDATE inventory SET quantity = ?
                    WHERE user_id = ? AND item_id = ?
                """, (new_quantity, user_id, item_id))
            else:
                conn.execute("""
                    INSERT INTO inventory (user_id, item_id, quantity)
                    VALUES (?, ?, ?)
                """, (user_id, item_id, quantity))

    def remove_item(self, user_id: int, item_id: str, quantity: int = 1):
        """Удаляет предмет из инвентаря"""
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            ).fetchone()

            if not existing:
                return False

            new_quantity = existing['quantity'] - quantity

            if new_quantity <= 0:
                conn.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                )
            else:
                conn.execute("""
                    UPDATE inventory SET quantity = ?
                    WHERE user_id = ? AND item_id = ?
                """, (new_quantity, user_id, item_id))

            return True

    def equip_item(self, user_id: int, item_id: str):
        """Экипирует предмет"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE inventory SET equipped = TRUE
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))

    def unequip_item(self, user_id: int, item_id: str):
        """Снимает предмет"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE inventory SET equipped = FALSE
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))

    # ==================== КВЕСТЫ ====================

    def start_quest(self, user_id: int, quest_id: str):
        """Начинает квест"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO active_quests (user_id, quest_id)
                VALUES (?, ?)
            """, (user_id, quest_id))

    def complete_quest(self, user_id: int, quest_id: str):
        """Завершает квест"""
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM active_quests WHERE user_id = ? AND quest_id = ?",
                (user_id, quest_id)
            )

            conn.execute("""
                INSERT OR IGNORE INTO completed_quests (user_id, quest_id)
                VALUES (?, ?)
            """, (user_id, quest_id))

    # ==================== БОЕВАЯ СИСТЕМА ====================

    def add_kill(self, user_id: int, enemy_id: str):
        """Добавляет убийство врага"""
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT count FROM kill_counts WHERE user_id = ? AND enemy_id = ?",
                (user_id, enemy_id)
            ).fetchone()

            if existing:
                new_count = existing['count'] + 1
                conn.execute("""
                    UPDATE kill_counts
                    SET count = ?, last_killed = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND enemy_id = ?
                """, (new_count, user_id, enemy_id))
            else:
                conn.execute("""
                    INSERT INTO kill_counts (user_id, enemy_id, count, last_killed)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                """, (user_id, enemy_id))

    def add_defeated_boss(self, user_id: int, boss_id: str):
        """Добавляет победу над боссом"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO defeated_bosses (user_id, boss_id)
                VALUES (?, ?)
            """, (user_id, boss_id))

    # ==================== СПОСОБНОСТИ ====================

    def add_ability(self, user_id: int, ability_name: str):
        """Добавляет способность игроку"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO player_abilities (user_id, ability_name)
                VALUES (?, ?)
            """, (user_id, ability_name))

    # ==================== ЭФФЕКТЫ ====================

    def add_effect(self, user_id: int, effect_name: str, effect_data: Dict, duration: int):
        """Добавляет эффект игроку"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO active_effects (user_id, effect_name, effect_data, duration)
                VALUES (?, ?, ?, ?)
            """, (user_id, effect_name, json.dumps(effect_data), duration))

    def remove_effect(self, user_id: int, effect_name: str):
        """Удаляет эффект"""
        with self.get_connection() as conn:
            conn.execute("""
                DELETE FROM active_effects
                WHERE user_id = ? AND effect_name = ?
            """, (user_id, effect_name))

    # ==================== СЮЖЕТ И ЛОКАЦИИ ====================

    def update_story_progress(self, user_id: int, city: str, scene_id: str):
        """Обновляет прогресс сюжета"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO story_progress (user_id, city, scene_id)
                VALUES (?, ?, ?)
            """, (user_id, city, scene_id))

    def unlock_location(self, user_id: int, location_id: str):
        """Открывает новую локацию"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO unlocked_locations (user_id, location_id)
                VALUES (?, ?)
            """, (user_id, location_id))

# Глобальный экземпляр базы данных
db = GameDatabase()
