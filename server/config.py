import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-goes-here'
    DATABASE_HOST = "mainline.proxy.rlwy.net"
    DATABASE_PORT = 23149
    DATABASE_USER = "root"
    DATABASE_PASSWORD = "uPilDXhcwYNlYwvcUACLfFgSOJwiGCaW"
    DATABASE_NAME = "railway"
