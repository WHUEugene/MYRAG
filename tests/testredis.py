import redis

try:
    # 建立Redis连接
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # 测试连接并打印结果
    result = r.ping()
    print(f"Redis连接测试结果: {result}")
    
    # 可选：测试基本操作
    r.set('test_key', 'hello')
    value = r.get('test_key')
    print(f"测试写入/读取: {value.decode('utf-8')}")
    
except redis.ConnectionError as e:
    print(f"Redis连接错误: {e}")
except Exception as e:
    print(f"发生错误: {e}")