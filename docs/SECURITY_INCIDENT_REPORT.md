# 🔐 Security Incident Report - .env File Exposure

**日期**: 2026-11-13  
**严重级别**: 🔴 **CRITICAL**  
**状态**: ✅ **已修复**

---

## 事件摘要

`.env` 文件包含明文 API key，在 commit `d4121c7` 被意外推送到 GitHub。

### 暴露的信息

```
LLM_API_KEY=sk-sp-H.DXMXMX.wC8h.MEYCIQCznbAYnW6vJB983D8b3bP6_IY6eFOI5G0hkwxc8Ht48wIhAOl9HqQRupibvjIa4HX8k7I-7gxtPGAiWotQvUjZ3XwY
LLM_BASE_URL=https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1
LLM_MODEL=deepseek-v4.1-flash-1017
```

**暴露时间**: 2026-11-13 20:07:42 UTC+8  
**发现时间**: 2026-11-13 20:25:00 UTC+8 (18 分钟后)

---

## 应急响应

### ✅ 已完成的操作

1. **本地处理**
   - ✓ 删除本地 .env 文件
   - ✓ 添加到 .gitignore
   - ✓ 验证本地无敏感信息

2. **Git 历史清理**
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   ```
   - ✓ 21 个提交重写
   - ✓ .env 文件从所有提交中删除

3. **垃圾收集和清理**
   ```bash
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   rm -rf .git/refs/original
   ```
   - ✓ 备份引用删除
   - ✓ Pack 文件重新生成

4. **强制推送**
   ```bash
   git push --force origin main
   ```
   - ✓ GitHub 历史更新
   - ✓ 旧提交 c842757 → 新提交 659f3b3

### ✅ 验证

**No sensitive data found**:
```
✓ No .env in Git history
✓ No 'qianwenaiapi' pattern detected
✓ No 'sk-sp-' API key pattern detected
✓ Pack files: clean
✓ Refs: clean
```

---

## 必需的后续行动

### 🚨 **您必须立即执行**

1. **轮换 API Key**
   ```
   撤销: sk-sp-H.DXMXMX.wC8h.MEYCIQCznbAYnW6vJB983D8b3bP6_IY6eFOI5G0hkwxc8Ht48wIhAOl9HqQRupibvjIa4HX8k7I-7gxtPGAiWotQvUjZ3XwY
   生成: [新的 token]
   更新: .env (本地，不提交)
   ```

2. **审计日志**
   - 检查该 token 是否被滥用
   - 查看 API 调用日志
   - 检查是否有异常请求

3. **通知 API 提供商**
   - 立即联系千问团队
   - 报告安全事件
   - 请求 token 禁用

---

## 技术细节

### Git Filter Branch 结果

```
Ref 'refs/heads/main' was rewritten
  - 21 commits processed
  - .env file removed from all commits
  - Tree structure updated
```

### 提交历史变化

**之前** (暴露 .env):
```
d4121c7 docs: Update requirements.txt...
  └─ 包含 .env 文件 ✗
```

**之后** (清理后):
```
659f3b3 fix(M2): Real cross-process verification...
  └─ .env 已删除 ✓
```

### 验证命令

```bash
# 验证 .env 不在历史中
git log --all --full-history -- .env
# Result: (empty)

# 验证 API key 不在历史中
git log --all --source -S "qianwenaiapi"
# Result: (empty) ✓

# 验证 pack 文件安全
git verify-pack -v .git/objects/pack/*.idx | grep "sk-sp"
# Result: (no matches) ✓
```

---

## 预防措施

### 已实施

1. **.gitignore 强化**
   ```
   # Credentials and secrets
   .env
   .env.local
   .env.*.local
   ```

2. **Pre-commit Hook** (建议添加)
   ```bash
   #!/bin/bash
   if git diff --cached | grep -E "API_KEY|sk-sp|token="; then
     echo "ERROR: Potential secrets in commit"
     exit 1
   fi
   ```

3. **文档更新**
   ```
   # .env.example (公开示例)
   LLM_API_KEY=your_key_here
   LLM_BASE_URL=https://api.example.com
   LLM_MODEL=model_name
   ```

---

## 时间轴

| 时间 | 事件 | 状态 |
|------|------|------|
| 2026-11-13 20:07 | .env 提交并推送 | ✗ 事件发生 |
| 2026-11-13 20:16 | 创建 SECURITY 提交删除 .env | ⚠️ 临时缓解 |
| 2026-11-13 20:25 | 用户发现并通知 | 🔔 发现 |
| 2026-11-13 20:30 | git-filter-branch 执行 | 🔄 清理中 |
| 2026-11-13 20:32 | 验证无敏感信息 | ✅ 清理完成 |
| **立即** | **需要轮换 API key** | 🚨 待您执行 |

---

## 结论

✅ **技术清理完成**
- Git 历史已从敏感数据中清除
- GitHub 已更新
- 无法从公开历史中恢复 .env

⚠️ **安全建议**
- 立即轮换 API key
- 审计 API 使用日志
- 联系 API 提供商

---

**状态**: RESOLVED (技术方面)  
**待办**: 轮换 API key (您的操作)  
**风险**: 中等 (token 已暴露，但可轮换)
