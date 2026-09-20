## irrp.py
### 参考
irrpによる実装
https://abyz.me.uk/rpi/pigpio/index.html
https://abyz.me.uk/rpi/pigpio/examples.html#Python%20code



### 赤外線記録例

```
python3 irrp.py -r -g18 -f codes.json rayair:on --no-confirm --post 130
```

### 実行例

```
python3 irrp.py -p -g22 -f codes.json light:on
```

### iot_client.py