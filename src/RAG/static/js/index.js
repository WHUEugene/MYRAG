document.addEventListener('DOMContentLoaded', function() {
    // 初始化模态框
    const modal = new bootstrap.Modal(document.getElementById('createKbModal'));
    
    // 绑定新建知识库按钮
    document.getElementById('createKbBtn').addEventListener('click', () => modal.show());
    
    // 加载知识库列表
    loadKnowledgeBases();
});

async function loadKnowledgeBases() {
    try {
        const response = await fetch('/api/knowledge-bases');
        const kbList = await response.json();
        
        const listContainer = document.getElementById('kbList');
        listContainer.innerHTML = kbList.map(kb => `
            <a href="/knowledge-base/${kb.id}" class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${kb.name}</h5>
                    <small>${new Date(kb.created_at).toLocaleString()}</small>
                </div>
            </a>
        `).join('');
    } catch (error) {
        console.error('加载知识库列表失败:', error);
        alert('加载知识库列表失败');
    }
}

async function createKb() {
    const nameInput = document.getElementById('kbName');
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('请输入知识库名称');
        return;
    }
    console.log("[DEBUG] createKb: 创建知识库，名称 =", name);
    try {
        const response = await fetch('/api/knowledge-base', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        const result = await response.json();
        console.log("[DEBUG] createKb: 服务端响应", result);
        if (result.id) {
            window.location.href = `/knowledge-base/${result.id}`;
        } else {
            throw new Error('创建失败');
        }
    } catch (error) {
        console.error("[DEBUG] createKb: 创建知识库失败", error);
        alert('创建知识库失败');
    }
}
