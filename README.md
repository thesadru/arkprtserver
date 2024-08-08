# arkprtserver

Website displaying arknights user information.

Built with [ArkPRTS](https://github.com/thesadru/ArkPRTS)

---

Source Code: https://github.com/thesadru/arkprtserver

---

## API docs

### `/api/raw/search?nickname=foo&server=[en|jp|kr]`
Returns raw data for an arknights user. Server defaults to `en`.

[example](https://arkprts.ashlen.top/api/raw/search?nickname=PeterYR)
```json
[{"nickName": "PeterYR", "nickNumber": "3977", "uid": "93679156", "registerTs": 1579195252, "mainStageProgress": null, "charCnt": 304, "furnCnt": 1537, "skinCnt": 213, ...
```

### `/api/search?nickname=foo&server=[en|jp|kr]&lang=[en|jp|kr|cn]`
Returns pretty data for an arknights user. Server defaults to `en`. Lang determines the static data language (such as character name) and defaults to the server lang.

[example](https://arkprts.ashlen.top/api/search?nickname=PeterYR)
```json
[{"nickname": "PeterYR", "nicknumber": "3977", "uid": "93679156", "server": "Terra", "level": 120, "avatar": {"type": "ICON", "id": "avatar_def_03", "asset": null}, ...
```

### `/api/login/sendcode?email=example%40gmail.com&server=[en|jp|kr]`
Sends an email with a code to the specified email address.

### `/api/login?email=example%40gmail.com&code=123456&server=[en|jp|kr]`
Logs in using the email and code (if they are currently in-game, this will kick them out). Returns authentication as both json and cookies (for compatibility).

Example: 
```json
{"server": "en", "channeluid": "12345678", "token": "..."}
```

### `/api/raw/user`
Returns private raw arknights user data. Requires authentication (`server, channeluid, token`) which can be sent anywhere in query, headers or cookies. Server can be any of `en, jp, kr, cn, bili, tw`.

If you are a bit familiar with the arknights internals, `uid, secret, seqnum` are also accepted.

[example (when logged in)](https://arkprts.ashlen.top/api/raw/user)
```json
{"dungeon": {"stages": {"main_00-01": {"stageId": "main_00-01", "completeTimes": 4, "startTimes": 5, "practiceTimes": 0, "state": 3, "hasBattleReplay": 1, "noCostCnt": 0}, ...
```


## Contributing

Any kind of contribution is welcome.
Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for more information.
