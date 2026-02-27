import sqlite3
import pprint

def check_db():
    conn = sqlite3.connect(r'D:\gst\data\adjudication.db')
    cursor = conn.cursor()
    cursor.execute("SELECT issue_id, active, sop_point, typeof(sop_point) FROM issues_master WHERE issue_id='LIABILITY_3B_R1'")
    res = cursor.fetchone()
    print("LIABILITY_3B_R1 DB Record:")
    pprint.pprint(res)
    
    conn.close()

if __name__ == '__main__':
    check_db()
