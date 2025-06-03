import matplotlib.pyplot as plt
import psycopg2
import time

MASTER_DB = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': '5433'
}

STANDBY_DB = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': '5434'
}

TABLE_NAME = 'data_table'
INSERTIONS = 1000
SLEEP = 0.025

class Logger:
    def __init__(self):
        self.timestamps = []
        self.master_count = []
        self.standby_count = []

    def get_count(self, db) -> int:
        try:
            with psycopg2.connect(**db) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
                    return cur.fetchone()[0]
        except Exception:
            return -1

    def log(self) -> None:
        self.timestamps.append(time.time())
        self.master_count.append(self.get_count(MASTER_DB))
        self.standby_count.append(self.get_count(STANDBY_DB))

    def plot(self) -> None:
        if not self.timestamps:
            print("Нет данных для отображения.")
            return

        t = [x - self.timestamps[0] for x in self.timestamps]

        valid_master = [c for c in self.master_count if c >= 0]
        valid_standby = [c for c in self.standby_count if c >= 0]

        max_master = max(valid_master) if valid_master else 0
        max_standby = max(valid_standby) if valid_standby else 0

        print(f"Количество записей в master: {max_master}/{len(t)}")
        print(f"Количество записей в standby: {max_standby}/{len(t)}")

        plt.figure(figsize=(10, 5))
        plt.plot(t, self.master_count, label='Master', marker='o')
        plt.plot(t, self.standby_count, label='Standby', linestyle='--')
        plt.xlabel("Время, с")
        plt.ylabel("Количество записей")
        plt.title("Количество записей в БД")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("insert_graph.png")
        print("График сохранён в insert_graph.png")

class Proxy:
    def __init__(self):
        self.use_primary = True
        self.successful_inserts = 0

    def promote(self) -> None:
        try:
            with psycopg2.connect(**STANDBY_DB) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_promote()")
                    conn.commit()
            print("Выполнен promote: standby стал новым master.")
        except Exception as e:
            print(f"Ошибка при promote: {e}")

    def _insert(self, db, value) -> bool:
        try:
            with psycopg2.connect(**db) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"INSERT INTO {TABLE_NAME} (data) VALUES (%s)", (value,))
                    conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка вставки: {e}")
            return False

    def insert(self, value) -> None:
        if self.use_primary:
            if self._insert(MASTER_DB, value):
                self.successful_inserts += 1
            else:
                print("Ошибка на master. Переключение...")
                self.use_primary = False
                self.promote()
                self._insert(STANDBY_DB, value)
        else:
            if self._insert(STANDBY_DB, value):
                self.successful_inserts += 1

def get_data() -> str:
    return 'test data'

def init_table() -> None:
    try:
        with psycopg2.connect(**MASTER_DB) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
                cur.execute(f"CREATE TABLE {TABLE_NAME} (id SERIAL PRIMARY KEY, data TEXT)")
                conn.commit()
        print(f"Таблица {TABLE_NAME} создана.")
    except Exception as e:
        print(f"Не удалось создать таблицу: {e}")

def main() -> None:
    init_table()
    proxy = Proxy()
    logger = Logger()

    for _ in range(INSERTIONS):
        value = get_data()
        proxy.insert(value)
        logger.log()
        time.sleep(SLEEP)

    logger.plot()

if __name__ == '__main__':
    main()
