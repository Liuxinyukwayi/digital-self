import os
from pathlib import Path


def verify_project():
    project_root = Path("D:\\ccuse\\mimo\\digital-self")

    required_files = [
        "docker-compose.yml",
        ".env.example",
        "README.md",
        "start.bat",
        "stop.bat",
        "backend/Dockerfile",
        "backend/requirements.txt",
        "backend/alembic.ini",
        "backend/app/main.py",
        "backend/app/core/config.py",
        "backend/app/core/database.py",
        "backend/app/models/models.py",
        "backend/app/services/mimo/mimo_client.py",
        "backend/app/services/persona/persona_service.py",
        "backend/app/services/memory/memory_service.py",
        "backend/app/services/knowledge/knowledge_service.py",
        "backend/app/services/rag/rag_service.py",
        "backend/app/services/agent/agent_service.py",
        "backend/app/services/distill/distill_service.py",
        "backend/app/services/sync/sync_service.py",
        "backend/app/api/v1/endpoints/chat.py",
        "backend/app/api/v1/endpoints/memory.py",
        "backend/app/api/v1/endpoints/knowledge.py",
        "backend/app/api/v1/endpoints/persona.py",
        "backend/app/api/v1/endpoints/sync.py",
        "frontend/package.json",
        "frontend/next.config.js",
        "frontend/tsconfig.json",
        "frontend/tailwind.config.js",
        "frontend/src/app/layout.tsx",
        "frontend/src/app/page.tsx",
        "frontend/src/app/chat/page.tsx",
        "frontend/src/app/timeline/page.tsx",
        "frontend/src/app/knowledge/page.tsx",
        "frontend/src/app/sync/page.tsx",
        "frontend/src/app/persona/page.tsx",
        "frontend/src/app/settings/page.tsx",
        "nginx/nginx.conf",
        "scripts/test_mimo.py",
        "scripts/test_backend.py",
        "scripts/init_db.py",
    ]

    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        print("缺少以下文件：")
        for f in missing_files:
            print(f"  - {f}")
        return False
    else:
        print("所有必需文件都存在！")
        return True


if __name__ == "__main__":
    verify_project()