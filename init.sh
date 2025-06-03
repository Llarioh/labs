# Ждём, пока primary-сервер станет доступен
until pg_isready -h master -p 5432 -U postgres; do
  echo "Ожидание доступности primary-сервера..."
  sleep 1
done

# Удаляем старые данные в каталоге standby-узла
echo "Очистка каталога данных standby..."
rm -rf /var/lib/postgresql/data/*

# Получаем полную копию данных с primary (через streaming replication)
echo "Создание резервной копии с primary-сервера..."
PGPASSWORD=postgres pg_basebackup -h master -D /var/lib/postgresql/data -U postgres -Fp -Xs -P -R

# Прописываем параметры подключения к primary в конфиг standby
echo "Настройка параметров подключения к primary..."
echo "primary_conninfo = 'host=master port=5432 user=postgres password=postgres'" >> /var/lib/postgresql/data/postgresql.auto.conf

# Устанавливаем корректные права на каталог данных
echo "Назначение прав доступа..."
chown -R postgres:postgres /var/lib/postgresql/data
chmod 700 /var/lib/postgresql/data

# Запускаем PostgreSQL в режиме standby с заданной конфигурацией
echo "Запуск PostgreSQL в standby-режиме..."
su postgres -c 'postgres -c config_file=/etc/postgresql/postgresql.conf -c hba_file=/etc/postgresql/pg_hba.conf'
