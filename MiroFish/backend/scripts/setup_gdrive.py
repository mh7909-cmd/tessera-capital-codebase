"""
Google Drive OAuth2 Setup Script
协助用户完成初次授权并生成 token.pickle
"""

import os
import pickle
import sys

# 确保能导入 backend 中的内容
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from google_auth_oauthlib.flow import InstalledAppFlow

# 定义权限范围
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    client_secrets_path = os.path.join(base_dir, 'client_secrets.json')
    token_path = os.path.join(base_dir, 'token.pickle')

    if not os.path.exists(client_secrets_path):
        print(f"Error: 找不到 {client_secrets_path}。请确保已创建该文件。")
        return

    print("--- Google Drive OAuth2 授权设置 ---")
    print("即将启动本地浏览器进行授权...")
    
    try:
        # 使用本地 8080 端口进行重定向（需在 Google Console 中配置一致）
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_path, SCOPES)
        creds = flow.run_local_server(port=8080)
        
        # 保存凭据
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            
        print(f"\n成功！授权令牌已保存至: {token_path}")
        print("现在后端可以代表你上传文件到 Google Drive 了。")
        
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        print("\n提示: 如果出现 'redirect_uri_mismatch'，请确保在 Google Cloud Console 中添加了 http://localhost:8080/ 到 Redirect URIs。")

if __name__ == "__main__":
    main()
