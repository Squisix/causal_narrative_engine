#!/bin/sh
# Script para configurar PostgreSQL con autenticación md5

# Esperar a que PostgreSQL esté listo
until pg_isready -U cne_user -d cne_db; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 1
done

# Modificar pg_hba.conf para usar md5 en lugar de scram-sha-256
echo "Configuring pg_hba.conf..."
cat > /var/lib/postgresql/data/pg_hba.conf <<EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     md5
host    all             all             0.0.0.0/0               md5
host    all             all             ::0/0                   md5
EOF

# Recargar configuración
pg_ctl reload -D /var/lib/postgresql/data

echo "PostgreSQL configuration updated successfully"
