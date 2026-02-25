import pandas as pd
import numpy as np


class DataProcessor:
    def __init__(self):
        self.df = None

    def load_and_merge(self, transactions_path: str, behavior_path: str):
        """
        Загрузка и объединение таблиц по cst_dim_id[cite: 38].
        """
        try:
            # Загрузка данных
            trx_df = pd.read_csv(transactions_path)
            beh_df = pd.read_csv(behavior_path)

            # Merge: Объединить таблицы по ID клиента
            # Предполагаем, что в обоих файлах есть колонка 'cst_dim_id' или аналогичная
            self.df = pd.merge(trx_df, beh_df, on='cst_dim_id', how='left')

            # Предварительная обработка дат (важно для velocity features)
            if 'transaction_dttm' in self.df.columns:
                self.df['transaction_dttm'] = pd.to_datetime(self.df['transaction_dttm'])
                self.df = self.df.sort_values(by=['cst_dim_id', 'transaction_dttm'])

            return self.df
        except Exception as e:
            raise ValueError(f"Ошибка при объединении файлов: {e}")

    def generate_features(self):
        """
        Генерация фичей согласно ТЗ v3.0 [cite: 39-44].
        """
        if self.df is None:
            raise ValueError("Данные не загружены. Сначала выполните load_and_merge.")

        # 1. is_new_device [cite: 40]
        # Сравниваем текущее устройство (device_id) с "любимым" (favorite_device)
        if 'device_id' in self.df.columns and 'favorite_device' in self.df.columns:
            self.df['is_new_device'] = (self.df['device_id'] != self.df['favorite_device']).astype(int)

        # 2. abnormal_login_frequency [cite: 41]
        # Если частота за 7 дней сильно выше средней за 30 дней
        if 'logins_last_7_days' in self.df.columns and 'logins_last_30_days' in self.df.columns:
            # Нормализуем 30 дней к неделе (делим на 4.28) для сравнения
            avg_weekly_login = self.df['logins_last_30_days'] / 4.28
            self.df['abnormal_login_frequency'] = (self.df['logins_last_7_days'] > (avg_weekly_login * 2)).astype(int)

        # 3. time_since_last_login [cite: 42]
        # Используем готовую колонку или mean_session_interval, если есть пропуски
        if 'time_since_last_login' in self.df.columns:
            self.df['time_since_last_login'] = self.df['time_since_last_login'].fillna(
                self.df['time_since_last_login'].mean())

        # 4. Velocity Features (Транзакции за последний час/сутки) [cite: 44]
        # Требует сортировки по времени (сделано в load_and_merge)
        if 'transaction_dttm' in self.df.columns and 'amount' in self.df.columns:
            # Группировка по клиенту и расчет скользящего окна
            # Внимание: это ресурсоемкая операция, для хакатона можно упростить
            grouped = self.df.groupby('cst_dim_id').rolling('1H', on='transaction_dttm')

            self.df['tx_count_1h'] = grouped['amount'].count().reset_index(level=0, drop=True)
            self.df['tx_sum_1h'] = grouped['amount'].sum().reset_index(level=0, drop=True)

            # Заполняем NaN (первые транзакции) нулями
            self.df['tx_count_1h'] = self.df['tx_count_1h'].fillna(0)
            self.df['tx_sum_1h'] = self.df['tx_sum_1h'].fillna(0)

        return self.df