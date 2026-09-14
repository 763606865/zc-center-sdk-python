# 发布到 PyPI

包名：`zc-center-sdk-python`  
导入名：`zc_center`  
协议：Apache-2.0（与 Spring Boot SDK 一致）

macOS / Homebrew Python **不要**直接对系统环境执行 `python3 -m pip install ...`，会触发 `externally-managed-environment`。一律使用虚拟环境。

## 1. 准备 PyPI 凭证

1. 注册 [https://pypi.org](https://pypi.org)（建议同时注册 [TestPyPI](https://test.pypi.org) 做演练）。
2. 账号 → Account settings → API tokens → Add API token。
3. 权限选「Entire account」或限定项目 `zc-center-sdk-python`。
4. 本机写入 `~/.pypirc`（勿提交到 Git）：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...你的正式 Token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZw...你的 TestPyPI Token
```

也可用环境变量：`TWINE_USERNAME=__token__`、`TWINE_PASSWORD=pypi-...`。

## 2. 发版前检查清单

- [ ] `pyproject.toml` 里 `version` 已递增（首次可为 `1.0.0`）
- [ ] `src/zc_center/__init__.py` 的 `__version__` 与上面一致
- [ ] README / CHANGELOG（如有）已更新
- [ ] 单测通过
- [ ] `LICENSE`、作者、仓库 URL 正确
- [ ] 包名 `zc-center-sdk-python` 在 PyPI 仍可用（或你已拥有该项目）

## 3. 构建与上传（推荐流程）

在 SDK 根目录（含 `pyproject.toml` 的目录）执行：

```bash
# 创建并进入虚拟环境（解决 externally-managed-environment）
python3 -m venv .venv
source .venv/bin/activate

# 安装本包 + 构建/发布工具
python -m pip install -U pip
python -m pip install -e ".[dev]"

# 跑测试
pytest -q

# 清理旧产物
rm -rf dist build *.egg-info src/*.egg-info

# 构建 sdist + wheel
python -m build

# 本地检查元数据
twine check dist/*

# 建议先上传 TestPyPI 验证
twine upload --repository testpypi dist/*

# 确认无误后再发正式 PyPI
twine upload dist/*
```

退出虚拟环境：`deactivate`。

## 4. 验证安装

```bash
# 正式源
python -m pip install zc-center-sdk-python==1.0.4

# 或从 TestPyPI 验证
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  zc-center-sdk-python==1.0.4

python -c "from zc_center import Client; import zc_center; print(zc_center.__version__)"
```

## 5. 后续版本

1. 改 `pyproject.toml` 的 `version` 与 `__version__`（例如 `1.0.1`）。
2. 提交并打 Git tag：`git tag v1.0.1 && git push origin v1.0.1`。
3. 重复第 3 节构建上传（**不要**覆盖已发布的同一版本号；PyPI 版本不可变）。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `externally-managed-environment` | 先 `python3 -m venv .venv && source .venv/bin/activate` |
| `File already exists` | 版本号已被占用，递增后再传 |
| 403 Invalid or non-existent authentication | Token 错误或未用 `__token__` 作用户名 |
| TestPyPI 装依赖失败 | 加 `--extra-index-url https://pypi.org/simple/` 拉 `requests` 等 |

## 不公开时的替代方式

仅内部使用可不发 PyPI：

```bash
pip install "git+https://github.com/763606865/zc-center-sdk-python.git@v1.0.0"
# 或
pip install -e /path/to/zc-center-sdk-python
```
