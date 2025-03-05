document.addEventListener('DOMContentLoaded', function() {
    const kbId = window.location.pathname.split('/').pop();
    
    console.log("[DEBUG] knowledge_base.js: 加载知识库配置，kbId =", kbId);
    loadKbConfig(kbId);
    
    console.log("[DEBUG] knowledge_base.js: 加载数据集列表");
    loadDatasets(kbId);
});

async function loadKbConfig(kbId) {
    try {
        const response = await fetch(`/api/knowledge-base/${kbId}/config`);
        if (response.status === 404) {
            // 自动创建配置文件
            console.info('配置文件不存在，自动创建中...');
            const defaultConfig = await createKbConfig(kbId);
            updateConfigUI(kbId, defaultConfig);
            return;
        }
        const config = await response.json();
        
        updateConfigUI(kbId, config);
    } catch (error) {
        console.error('加载知识库配置失败:', error);
        alert('加载知识库配置失败');
    }
}

function updateConfigUI(kbId, config) {
    document.getElementById('kbId').textContent = kbId;
    document.getElementById('embeddingModel').value = config.embedding_model;
    document.getElementById('textModel').value = config.text_model;
}

// 新增函数，用于自动创建配置文件
async function createKbConfig(kbId) {
    console.log("[DEBUG] createKbConfig: 自动创建配置, kbId =", kbId);
    try {
        const response = await fetch(`/api/knowledge-base/${kbId}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ embedding_model: 'default_embedding', text_model: 'default_text' })
        });
        const config = await response.json();
        console.log("[DEBUG] createKbConfig: 创建配置响应", config);
        if (config.success) {
            alert('配置文件自动创建成功');
            return config;
        } else {
            throw new Error('自动创建失败');
        }
    } catch (error) {
        console.error("[DEBUG] createKbConfig: 自动创建配置失败", error);
        alert('自动创建配置失败');
        return { embedding_model: '', text_model: '' };
    }
}

async function saveConfig() {
    const kbId = window.location.pathname.split('/').pop();
    const embeddingModel = document.getElementById('embeddingModel').value;
    const textModel = document.getElementById('textModel').value;
    console.log("[DEBUG] saveConfig: 即将保存配置", { kbId, embeddingModel, textModel });
    
    try {
        const response = await fetch(`/api/knowledge-base/${kbId}/config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ embedding_model: embeddingModel, text_model: textModel })
        });
        
        const result = await response.json();
        console.log("[DEBUG] saveConfig: 服务端响应", result);
        if (result.success) {
            alert('配置保存成功');
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error("[DEBUG] saveConfig: 保存配置失败", error);
        alert('保存配置失败');
    }
}

async function loadDatasets(kbId) {
    try {
        const response = await fetch(`/api/knowledge-base/${kbId}/datasets`);
        const datasets = await response.json();
        
        const tableBody = document.querySelector('#datasetList tbody');
        tableBody.innerHTML = datasets.map(dataset => `
            <tr>
                <td>${dataset.name}</td>
                <td>${dataset.status}</td>
                <td>${dataset.total_count || 0}</td>
                <td>${new Date(dataset.created_at).toLocaleString()}</td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" 
                               ${dataset.enabled ? 'checked' : ''}
                               onchange="toggleDataset('${dataset.id}', this.checked)"
                               ${dataset.status === 'PROCESSING' ? 'disabled' : ''}>
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-danger" 
                            onclick="deleteDataset('${dataset.id}')">
                        删除
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('加载数据集列表失败:', error);
        alert('加载数据集列表失败');
    }
}

async function toggleDataset(datasetId, enabled) {
    try {
        const response = await fetch(`/api/dataset/${datasetId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled: enabled })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        if (result.success) {
            // 操作成功,不需要刷新整个页面
            console.log(`数据集 ${datasetId} ${enabled ? '已启用' : '已禁用'}`);
        } else {
            throw new Error(result.error || '操作失败');
        }
    } catch (error) {
        console.error('更新数据集状态失败:', error);
        alert('更新数据集状态失败: ' + error.message);
        // 恢复checkbox状态
        const kbId = document.getElementById('kbId').textContent;
        await loadDatasets(kbId);
    }
}

async function deleteDataset(datasetId) {
    if (!confirm('确定要删除这个数据集吗？删除后将无法恢复！')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/dataset/${datasetId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        if (result.success) {
            // 重新加载数据集列表
            const kbId = document.getElementById('kbId').textContent;
            await loadDatasets(kbId);
        } else {
            throw new Error(result.error || '删除失败');
        }
    } catch (error) {
        console.error('删除数据集失败:', error);
        alert('删除数据集失败: ' + error.message);
    }
}
