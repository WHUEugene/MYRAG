document.addEventListener('DOMContentLoaded', function() {
    // 修改为直接使用 .value 获取隐藏 input 的值
    const kbId = document.getElementById('kbId').value;
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const uploadBtn = document.getElementById('uploadBtn');
    const previewContent = document.getElementById('previewContent');
    
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
    });
    fileInput.addEventListener('change', handleFileSelect);
    uploadBtn.addEventListener('click', uploadFile);
    
    function handleFileSelect() {
        console.log("[DEBUG] handleFileSelect: 文件选择变化", fileInput.files);
        const file = fileInput.files[0];
        if (file) {
            previewFile(file);
            uploadBtn.disabled = false;
        } else {
            previewContent.textContent = '';
            uploadBtn.disabled = true;
        }
    }
    
    async function previewFile(file) {
        console.log("[DEBUG] previewFile: 预览文件", file.name);
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`/api/knowledge-base/${kbId}/preview`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            console.log("[DEBUG] previewFile: 预览结果", result);
            previewContent.textContent = result.preview;
        } catch (error) {
            console.error("[DEBUG] previewFile: 文件预览失败", error);
            alert('文件预览失败');
        }
    }
    
    async function uploadFile() {
        console.log("[DEBUG] uploadFile: 开始上传");
        const file = fileInput.files[0];
        const chunkSize = document.getElementById('chunkSize').value;
        const overlap = document.getElementById('overlap').value;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('chunk_size', chunkSize);
        formData.append('overlap', overlap);
        
        try {
            const response = await fetch(`/api/knowledge-base/${kbId}/upload`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            console.log("[DEBUG] uploadFile: 上传响应", result);
            if (result.success) {
                alert('文件上传成功');
                window.location.href = `/knowledge-base/${kbId}`;
            } else {
                throw new Error('上传失败');
            }
        } catch (error) {
            console.error("[DEBUG] uploadFile: 文件上传失败", error);
            alert('文件上传失败');
        }
    }
});
