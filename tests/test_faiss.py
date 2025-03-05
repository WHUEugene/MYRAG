import numpy as np
import faiss

def test_faiss_installation():
    # 创建一个简单的向量集合
    d = 64                           # 向量维度
    nb = 100                         # 数据库大小
    np.random.seed(1234)             # 使结果可重现
    xb = np.random.random((nb, d)).astype('float32')
    
    # 创建索引
    index = faiss.IndexFlatL2(d)   
    index.add(xb)                  
    
    # 测试搜索
    k = 4                          # 要查找的最近邻数量
    xq = np.random.random((1, d)).astype('float32')
    D, I = index.search(xq, k)     
    
    print("测试成功!")
    print(f"找到的最近{k}个向量的距离: {D}")
    print(f"找到的最近{k}个向量的索引: {I}")

import numpy as np
import faiss

def test_faiss_performance(vector_dim=64, num_vectors=100000):
    """测试FAISS在不同规模数据下的性能"""
    # 创建测试数据
    print(f"生成{num_vectors}个{vector_dim}维向量...")
    vectors = np.random.random((num_vectors, vector_dim)).astype('float32')
    
    # 1. 基础IndexFlatL2
    index_flat = faiss.IndexFlatL2(vector_dim)
    print("\n测试IndexFlatL2:")
    import time
    start = time.time()
    index_flat.add(vectors)
    print(f"索引构建时间: {time.time() - start:.2f}秒")
    
    # 2. 使用IVF索引(更快的搜索)
    nlist = 100  # 聚类中心数量
    quantizer = faiss.IndexFlatL2(vector_dim)
    index_ivf = faiss.IndexIVFFlat(quantizer, vector_dim, nlist)
    index_ivf.train(vectors)
    print("\n测试IndexIVFFlat:")
    start = time.time()
    index_ivf.add(vectors)
    print(f"IVF索引构建时间: {time.time() - start:.2f}秒")
    
    # 搜索性能测试
    query = np.random.random((1, vector_dim)).astype('float32')
    k = 4
    
    print("\n搜索性能测试:")
    start = time.time()
    D1, I1 = index_flat.search(query, k)
    print(f"FlatL2搜索时间: {time.time() - start:.4f}秒")
    
    start = time.time()
    D2, I2 = index_ivf.search(query, k)
    print(f"IVF搜索时间: {time.time() - start:.4f}秒")


    
if __name__ == "__main__":
    test_faiss_installation()
    test_faiss_performance()