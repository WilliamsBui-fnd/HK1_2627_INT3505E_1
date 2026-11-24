# Tuần 9 - API Versioning

## Lab 1 - URI Path Versioning (port 5055)

```
cd Tuan_9/lab1
python3 app.py
curl localhost:5055/api/v1/users/1
curl localhost:5055/api/v2/users/1
```

![lab1 server](lab1/screenshots/lab1_1.png)

![lab1 curl](lab1/screenshots/lab1_2.png)

![lab1 curl](lab1/screenshots/lab1_3.png)

## Lab 2 - Header Versioning (port 5056)

```
cd Tuan_9/lab2
python3 app.py
```

```
curl -i localhost:5056/users/1
curl -i -H 'X-API-Version: 1' localhost:5056/users/1
curl -i -H 'X-API-Version: 2024-06-20' localhost:5056/users/1
curl -i -H 'X-API-Version: 99' localhost:5056/users/1
```

![lab2 server](lab2/screenshots/lab2_1.png)

![lab2 curl](lab2/screenshots/lab2_2.png)

## Lab 3 - Sunset Middleware (port 5057)

```
cd Tuan_9/lab3
python3 app.py
```

```
curl -i localhost:5057/api/v1/users/1
curl -i localhost:5057/api/v0/users/1
```

![lab3 server](lab3/screenshots/lab3_1.png)

![lab3 curl](lab3/screenshots/lab3_2.png)

## Lab 4 - Blue-Green Routing (port 5058)

```
cd Tuan_9/lab4
python3 app.py
```

```
curl -i -X POST -H 'Content-Type: application/json' -H 'X-Cohort: beta' -d '{"account_id":"any"}' localhost:5058/orders
curl -i -X POST -H 'Content-Type: application/json' -d '{"account_id":"acct_42"}' localhost:5058/orders
curl -i -X POST -H 'Content-Type: application/json' -d '{"account_id":"user_1"}' localhost:5058/orders
```

![lab4 server](lab4/screenshots/lab4_1.png)

![lab4 curl](lab4/screenshots/lab4_2.png)

## Test tự động

```
cd Tuan_9/lab2 && python3 test_lab2.py
cd Tuan_9/lab3 && python3 test_lab3.py
cd Tuan_9/lab4 && python3 test_lab4.py
```
