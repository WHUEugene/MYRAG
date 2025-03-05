# API请求格式参考

本文档提供了使用视觉模型API的正确请求格式。

## 阿里云通义千问2.5-VL模型

通义千问2.5-VL模型支持图像理解和处理，以下是正确的请求格式：

### 请求头部

```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer YOUR_API_KEY"
}
```

### 请求体

```json
{
  "model": "qwen2-vl-7b-instruct",
  "messages": [
    {
      "role": "system",
      "content": "你是一个图像描述专家。请详细描述这张图片内容。"
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "请描述这张图片的内容。"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA..."
          }
        }
      ]
    }
  ],
  "max_tokens": 500
}
```

### 重要注意事项

1. 图片URL必须使用以下格式：
   ```
   data:image/jpeg;base64,YOUR_BASE64_ENCODED_IMAGE
   ```

2. base64编码的图片数据不应包含换行符或额外的空格

3. 确保base64编码使用正确的MIME类型（如image/jpeg, image/png等）

4. 图片大小不要过大，建议压缩到1MB以内

## 常见的错误与解决方法

### 400 Bad Request - "Image url should be a valid url or should like data:image/TYPE;base64,..."

这个错误表示提供的图片URL格式不正确。请检查：

- base64字符串是否完整且有效
- MIME类型是否正确（如image/jpeg）
- 确保格式为 `data:image/TYPE;base64,YOUR_BASE64_CONTENT`

### 413 Payload Too Large

图片太大。请尝试：
- 压缩图片
- 降低分辨率
- 使用JPEG格式（通常比PNG小）

### 429 Too Many Requests

API请求频率过高。请减少请求频率或联系服务提供商增加配额。
