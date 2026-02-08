# subskill: build-check

## 触发条件

- 任意代码改动完成后。

## 执行动作

```bash
bash scripts/check_errors.sh
```

按需补充：

```bash
npm test
```

## 通过标准

1. 质量门禁返回 0。
2. 失败项修复后复跑。
