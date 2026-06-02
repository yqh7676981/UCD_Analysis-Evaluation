"""
OpenAI 客户端封装模块
为 benchmark 项目提供流式对话和 JSON 提取工具
"""

import time
import json
import re
import base64
from io import BytesIO
from typing import List, Dict, Optional, Union
import httpx
from PIL import Image
from openai import OpenAI
from util.config_loader import config



class OpenAIClient:
    """OpenAI 客户端封装类，支持流式输出和 JSON 提取"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        初始化 OpenAI 客户端

        Args:
            api_key: API 密钥（默认从 config.API_KEY 读取）
            base_url: API 地址（默认从 config.URL 读取）
            model: 模型名称（默认从 config.MODEL 读取）
            verify_ssl: 是否验证 SSL 证书
        """
        self.api_key = api_key or config.api_key
        self.base_url = base_url or config.url
        self.model = model or config.model

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.Client(verify=verify_ssl)
        )

    def chat(
        self,
        messages: List[Dict[str, Union[str, List]]],
        model: Optional[str] = None,
        stream: bool = True,
        max_tokens: int = 32768,
        label: str = "对话",
        verbose: bool = True
    ) -> str:
        """
        发送对话请求，支持流式输出

        Args:
            messages: 消息列表，每个消息包含 'role' 和 'content'
            model: 模型名称（默认使用 self.model）
            stream: 是否启用流式输出
            max_tokens: 最大生成 token 数
            label: 统计信息标签
            verbose: 是否打印流式输出和统计信息

        Returns:
            完整的响应文本
        """
        try:
            model = model or self.model

            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                max_tokens=max_tokens
            )

            full_content = ""
            tokens_num = 0
            time_start = time.time()

            for chunk in completion:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        tokens_num += len(content)
                        full_content += content
                        if verbose:
                            print(content, end="", flush=True)

            elapsed = time.time() - time_start

            if verbose:
                print(f"\n\n--- 【{label}】统计 ---")
                print(f"输出长度: {tokens_num} chars | 耗时: {elapsed:.2f}s | 速度: {tokens_num/elapsed:.1f} chars/s")
            return full_content
        except Exception as e:
            print(e)
            return "error"

    def chat_simple(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 32768,
        label: str = "对话",
        verbose: bool = False
    ) -> str:
        """
        简单对话，单条用户消息

        Args:
            prompt: 用户提示词
            model: 模型名称（默认使用 self.model）
            max_tokens: 最大生成 token 数
            label: 统计信息标签
            verbose: 是否打印流式输出

        Returns:
            完整的响应文本
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            label=label,
            verbose=verbose
        )

    def chat_with_image(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
        max_tokens: int = 32768,
        label: str = "视觉",
        verbose: bool = True,
    ) -> str:
        """
        图文对话，支持文本和图片输入
        自动压缩超过大小限制的图片（默认 750KB，base64 后约 1MB）

        Args:
            prompt: 文本提示词
            image_base64: Base64 编码的图片
            model: 模型名称（默认使用 self.model）
            max_tokens: 最大生成 token 数
            label: 统计信息标签
            verbose: 是否打印流式输出
            max_image_size: 原始图片最大字节数（默认 750KB）

        Returns:
            完整的响应文本
        """
        # 压缩图片（如果需要），返回压缩后的 base64 和 MIME 类型
        compressed_b64, mime_type = self._compress_image_if_needed(image_base64)
        print(prompt)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{compressed_b64}",
                    },
                },
            ],
        }]
        return self.chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            label=label,
            verbose=verbose
        )

    @staticmethod
    def _compress_image_if_needed(image_base64: str, max_size: int = 800_000) -> tuple[str, str]:
        """
        压缩图片到目标大小以下（默认 300KB）
        使用迭代压缩确保最终结果一定在限制以内

        Args:
            image_base64: Base64 编码的图片
            max_size: 原始图片最大字节数（默认 300KB）

        Returns:
            (压缩后的 base64 字符串, MIME 类型)
        """
        # 先解码检查大小
        try:
            img_data = base64.b64decode(image_base64)
        except Exception:
            # 解码失败，直接返回原字符串，假设为 PNG
            return image_base64, "image/png"

        original_size = len(img_data)

        # 尝试检测原始格式
        try:
            img = Image.open(BytesIO(img_data))
            original_fmt = img.format.lower() if img.format else "png"
        except Exception:
            return image_base64, "image/png"

        # 如果已经小于限制，直接返回
        if original_size <= max_size:
            fmt = img.format.lower() if img.format else "png"
            return image_base64, f"image/{fmt}"

        # 需要压缩
        print(f"[图片压缩] 原图 {original_size/1024:.1f}KB > {max_size/1024:.1f}KB，开始压缩...")

        try:
            # 转换为 RGB（去除透明通道以减小体积）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # 迭代压缩：逐步降低质量和尺寸直到满足要求
            quality = 85
            scale = 1.0
            min_quality = 30
            min_dimension = 200
            while True:
                # 计算新尺寸
                new_width = max(int(img.width * scale), min_dimension)
                new_height = max(int(img.height * scale), min_dimension)

                # 缩放图片
                if new_width < img.width or new_height < img.height:
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img

                # img_resized.show()
                # 保存为 JPEG
                output = BytesIO()
                img_resized.save(output, format='JPEG', quality=quality, optimize=True)
                compressed_data = output.getvalue()
                compressed_size = len(compressed_data)
                print("compressed_size: ", compressed_size,"max_size: ", max_size)
                # 检查是否满足要求
                if compressed_size <= max_size:
                    compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
                    print(f"[图片压缩] 完成: {original_size/1024:.1f}KB -> {compressed_size/1024:.1f}KB"
                          f" (尺寸: {img.width}x{img.height} -> {new_width}x{new_height}, 质量: {quality}%)")
                    return compressed_b64, "image/jpeg"

                # 不满足要求，调整参数继续压缩
                if quality > min_quality:
                    # 先降低质量
                    quality -= 10
                else:
                    # 质量已经很低了，缩小尺寸
                    scale *= 0.8
                    quality = 85  # 重置质量尝试新的尺寸

                # 防止无限循环
                if new_width <= min_dimension or new_height <= min_dimension:
                    # 已经达到最小尺寸，强制返回当前结果
                    compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
                    print(f"[图片压缩] 警告: 已压缩到最小尺寸仍超过 {max_size/1024:.1f}KB，"
                          f"当前 {compressed_size/1024:.1f}KB")
                    return compressed_b64, "image/jpeg"

        except Exception as e:
            print(f"[图片压缩] 压缩失败，使用原图: {e}")
            return image_base64, "image/png"

    @staticmethod
    def extract_json(text: str, raise_on_error: bool = True) -> Union[dict, str]:
        """
        从模型输出中提取 JSON 对象
        支持 ```json ... ``` 包裹格式

        Args:
            text: 模型输出的原始文本
            raise_on_error: 解析失败时是否抛出异常（False 则返回原文本）

        Returns:
            解析后的字典，或 raise_on_error=False 时返回原文本

        Raises:
            ValueError: raise_on_error=True 且 JSON 解析失败时抛出
        """
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text.strip())
        except (json.JSONDecodeError, Exception) as e:
            if raise_on_error:
                raise ValueError(f"JSON 解析失败: {e}")
            return text


# 便捷函数：获取客户端实例
def get_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    verify_ssl: bool = False
) -> OpenAIClient:
    """获取新的 OpenAIClient 实例，支持参数覆盖"""
    return OpenAIClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        verify_ssl=verify_ssl
    )


if __name__ == "__main__":
    # 简单测试
    print("OpenAIClient 配置信息:")
    client = OpenAIClient()
    print(f"  模型: {client.model}")
    print(f"  API 地址: {client.base_url}")
    print(f"  API 密钥已设置: {bool(client.api_key)}")
    print("\n客户端初始化成功!")
