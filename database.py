import sqlite3

def setup():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS scheduled_messages (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   channel_id INTEGER,                  
                   user_id INTEGER,
                   message_content TEXT,
                   send_at INTEGER
                   )''')
                   
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                   user_id INTEGER PRIMARY KEY,
                   timezone TEXT
                   )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS role_assigner (
                   message_id INTEGER,
                   reaction TEXT,
                   role_name TEXT
                   )''')
       
    conn.commit()
    conn.close()
    print("Database initialized!")