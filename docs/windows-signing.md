# Windows 发布者信任与签名

Windows 的“未知发布者”“无法信任”提示与代码签名、文件信誉及设备策略有关。程序可以通过启动自检，却仍然没有受信任的发布者。SHA-256 证明下载文件与发布包一致，不代表发布者已受信任。

当前没有向本项目提供经过身份验证的签名账户。没有签名时，发布包必须明确记录 `NotSigned`，不能声称消除了提示。有效签名可以显示经过验证的发布者，但新文件仍可能出现 SmartScreen 信誉提示。

## 发布维护者配置

CI 使用 Microsoft Azure Artifact Signing 的 Public Trust 证书配置，通过 OIDC 登录。维护者须先自行完成服务的账户、地区资格、付费与身份验证。此仓库不会自动创建、购买或替用户提交身份资料。

1. 创建经过验证的 Public Trust certificate profile；将应用身份的签名角色限制到所需证书配置。
2. 配置 GitHub OIDC 联合身份：issuer `https://token.actions.githubusercontent.com`，subject **`repo:zerlinpi/Product-QC-Daily:ref:refs/heads/main`**，audience `api://AzureADTokenExchange`。不要授权分支通配符或 pull request 身份。
3. 在仓库 Actions secrets 配置 `AZURE_CLIENT_ID`、`AZURE_TENANT_ID`、`AZURE_SUBSCRIPTION_ID`，无需导出私钥或保存长期 client secret。
4. 在 Actions variables 配置下列公开参数：

| 变量 | 内容 |
| --- | --- |
| `QC_SIGNING_ENDPOINT` | 账户所在区域的 HTTPS codesigning.azure.net 端点 |
| `QC_SIGNING_ACCOUNT` | Artifact Signing 账户名 |
| `QC_SIGNING_PROFILE` | 已完成验证的 Public Trust 证书配置名 |
| `QC_SIGNING_PUBLISHER` | 预期签名证书的完整 Subject 字符串，按证书原样填写 |
| `QC_SIGNING_ENABLED` | 完成上述配置后设为 `true`；未配置时留空或设 `false` |

只有 `main` 的 push 构建会使用签名身份。PR 和开发分支只生成未签名验证包。GitHub main 分支保护与 OIDC subject 限制需共同生效。

## 构建顺序与校验

双平台 pytest / Ruff、LibreOffice 实际重算 → Windows PyInstaller onedir → 校验未签名构建与失败路径 →（已启用时）对未签名的 EXE/DLL/PYD 签名并附加 RFC3161 SHA-256 时间戳 → Authenticode 校验 → 实际 EXE 自检 → ZIP/SHA-256 → 精确 main SHA Release。

有效的第三方签名保留；无效或被修改的签名会使流水线失败。启用签名后，任一可执行文件仍未签名、主 EXE 发布者不符或缺少时间戳，均阻止发布，不退回未签名包。ZIP 内 `signature-verification.json` 记录各文件 SHA-256、真实签名状态、发布者、证书指纹和时间戳证书指纹。签名后不再改写二进制文件。

未启用签名时，签名报告只证明已检查并如实报告未签名状态，不等同于“信任问题已修复”。配置服务后，还需在独立 Windows 电脑验证证书链、实际发布者名称、SmartScreen/Smart App Control 提示与设备策略；CI 自检不能代替该验收。

本项目不关闭 Defender/SmartScreen，不移除下载来源标记，也不安装自签根证书来掩盖问题。

参考：[Microsoft SmartScreen 文档](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)、[Artifact Signing Action](https://github.com/Azure/artifact-signing-action)、[OIDC 配置](https://github.com/Azure/artifact-signing-action/blob/main/docs/OIDC.md)。
