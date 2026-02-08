# subskill: git-management

## 触发条件

- 阶段成果形成
- 大改动前后
- 需要回滚锚点

## 建议动作

```bash
git add -A
git commit -m "<type>: <milestone-summary>"
```

可选保护点：

```bash
git branch backup/<date>-<topic>
git tag -a checkpoint/<date>-<topic> -m "before large change"
```
