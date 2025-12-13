#!/usr/bin/env python3
"""
测试脚本：验证 zai-sdk 是否正确安装
"""

def test_zai_import():
    """测试 zai 模块导入"""
    try:
        from zai import ZhipuAiClient
        print("✅ zai-sdk 导入成功！")
        
        # 尝试获取版本号
        import zai
        version = getattr(zai, '__version__', '未知版本')
        print(f"📦 zai-sdk 版本: {version}")
        
        # 测试客户端初始化（不实际调用API）
        try:
            client = ZhipuAiClient(api_key="test_key")
            print("✅ ZhipuAiClient 初始化成功！")
        except Exception as e:
            print(f"⚠️  ZhipuAiClient 初始化失败: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ zai-sdk 导入失败: {e}")
        print("\n请运行以下命令安装：")
        print("  pip install zai-sdk")
        return False

def test_flask_imports():
    """测试 Flask 相关导入"""
    try:
        from flask import Flask, Response, stream_with_context
        print("✅ Flask 相关模块导入成功！")
        return True
    except ImportError as e:
        print(f"❌ Flask 导入失败: {e}")
        print("\n请运行以下命令安装：")
        print("  pip install -r requirements.txt")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("🔍 测试 AI 助手依赖项")
    print("=" * 50)
    print()
    
    flask_ok = test_flask_imports()
    print()
    zai_ok = test_zai_import()
    print()
    
    print("=" * 50)
    if flask_ok and zai_ok:
        print("🎉 所有依赖项检查通过！")
        print("✅ 可以正常启动 AI 助手功能了！")
    else:
        print("⚠️  存在缺失的依赖项，请先安装")
        print("\n快速安装命令：")
        print("  pip install -r requirements.txt")
    print("=" * 50)

