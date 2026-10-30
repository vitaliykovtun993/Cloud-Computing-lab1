# Розгортання PARCS-Python у Google Cloud і заміри

План відрізняється від методички (`PARCS-Python_Google_Cloud_0925.pdf`) у трьох місцях:

1. **Не `create-with-container`.** Google оголосив цю команду і агент запуску контейнерів
   застарілими ([документація](https://docs.cloud.google.com/compute/docs/containers/deploying-containers)).
   Замість неї VM на Container-Optimized OS (COS) запускає той самий образ `hummer12007/parcs-node`
   через `docker run` у стартовому скрипті — так рекомендує сам Google.
2. **Не відкриваємо всі порти всьому інтернету.** Веб-інтерфейс PARCS без пароля приймає й виконує
   будь-який Python-код, тому порт 8080 відкриваємо лише для своєї IP-адреси.
3. **Команди зібрані так, щоб їх можна було копіювати.** У методичці є типографські лапки `“…”`
   і довге тире `—source-ranges`, через які команди не працюють.

Усі команди `gcloud` виконуються в **Cloud Shell**: кнопка `>_` угорі праворуч у
[console.cloud.google.com](https://console.cloud.google.com). Там уже є `gcloud`, `git` і bash,
нічого не треба ставити на Windows. Команди для Windows (PowerShell) позначені окремо.

---

## Крок 0. Підготовка локально (Windows, PowerShell, папка проєкту)

### 0.1. Перевірити, що все працює

```powershell
python -m unittest test_kmp test_solver
python run_solver_local.py data/small.txt --workers 4
```

### 0.2. Згенерувати вхідні файли для PARCS

Seed фіксований, тому ті самі команди в хмарі дадуть побайтово такі самі файли
(це знадобиться для послідовного заміру в кроці 6).

```powershell
python data_generator.py --size-mb 10  --pattern-length 12 --insert 100  --seed 42 -o data/text_10mb.txt
python data_generator.py --size-mb 100 --pattern-length 12 --insert 1000 --seed 42 -o data/text_100mb.txt
```

Контрольна сума (для звіту і для звірки з хмарою):

```powershell
certutil -hashfile data\text_100mb.txt MD5
```

### 0.3. Залити код на GitHub (умова лаби вимагає цього)

Перед цим видали з `results/sequential.csv` демонстраційні рядки з ноутбука.
PDF з умовою комітити необов'язково.

1. На github.com створи **порожній** репозиторій (без README), наприклад `Cloud-Computing-lab1`.
2. У PowerShell у папці проєкту:

```powershell
git init
git add .
git commit -m "KMP: sequential version, data generator, PARCS solver"
git branch -M main
git remote add origin https://github.com/vitaliykovtun993/Cloud-Computing-lab1.git
git push -u origin main
```

---

## Крок 1. Проєкт Google Cloud (Cloud Shell)

Обери ID проєкту: малі латинські літери, цифри і дефіс, 6–30 символів, унікальний на весь Google Cloud.

```bash
PROJECT_ID=kmp-parcs-<прізвище>-1
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
```

Прив'яжи платіжний акаунт (там лежать безкоштовні кредити):

```bash
gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=<ACCOUNT_ID зі списку вище>
```

Увімкни Compute Engine (займає 1–2 хвилини) і задай зону:

```bash
gcloud services enable compute.googleapis.com
gcloud config set compute/zone europe-north1-a
gcloud config set compute/region europe-north1
```

`gcloud config` зберігається між сесіями Cloud Shell, тому `--zone` далі не потрібен.

---

## Крок 2. Фаєрвол

Дізнайся свою публічну IP-адресу: відкрий https://ifconfig.me **у своєму браузері**, не в Cloud Shell,
бо там буде адреса Cloud Shell.

```bash
MY_IP=<твоя IP-адреса>

# PARCS-вузли спілкуються між собою на випадкових портах — дозволяємо все всередині мережі
gcloud compute firewall-rules create parcs-internal --network=default --direction=INGRESS \
  --action=ALLOW --rules=tcp,udp,icmp --source-ranges=10.128.0.0/9 --target-tags=parcs

# веб-інтерфейс PARCS — лише з твоєї адреси
gcloud compute firewall-rules create parcs-ui --network=default --direction=INGRESS \
  --action=ALLOW --rules=tcp:8080 --source-ranges=$MY_IP/32 --target-tags=parcs
```

Якщо домашня IP-адреса зміниться (сторінка перестане відкриватися), онови правило:

```bash
gcloud compute firewall-rules update parcs-ui --source-ranges=<нова IP>/32
```

---

## Крок 3. Master

```bash
cat > master.sh <<'EOF'
#!/bin/bash
# COS за замовчуванням блокує вхідні з'єднання на рівні ОС; доступ обмежує фаєрвол VPC
iptables -A INPUT -j ACCEPT
docker rm -f parcs || true
docker run -d --name parcs --restart=always --network=host \
  -e PARCS_ARGS="master" hummer12007/parcs-node
EOF

gcloud compute instances create master --machine-type=n1-standard-1 \
  --image-family=cos-stable --image-project=cos-cloud --tags=parcs \
  --metadata-from-file=startup-script=master.sh
```

Внутрішня IP master (потрібна воркерам):

```bash
MASTER_IP=$(gcloud compute instances describe master --format='get(networkInterfaces[0].networkIP)')
echo $MASTER_IP
```

Зачекай 1–2 хвилини і відкрий у браузері `http://<EXTERNAL_IP master>:8080`.
Зовнішню адресу показує `gcloud compute instances list`. Має відкритися сторінка «PARCS home page».

---

## Крок 4. Воркери

Лапки в `<<EOF` тут навмисно **без** апострофів, щоб `${MASTER_IP}` підставився у скрипт.

```bash
cat > worker.sh <<EOF
#!/bin/bash
iptables -A INPUT -j ACCEPT
docker rm -f parcs || true
docker run -d --name parcs --restart=always --network=host \
  -e PARCS_ARGS="worker ${MASTER_IP}" hummer12007/parcs-node
EOF

cat worker.sh   # перевір, що в рядку PARCS_ARGS стоїть справжня IP, а не порожньо
```

```bash
gcloud compute instances create worker1 worker2 worker3 worker4 worker5 worker6 \
  --machine-type=n1-standard-1 --image-family=cos-stable --image-project=cos-cloud \
  --tags=parcs --metadata-from-file=startup-script=worker.sh
```

Через 1–2 хвилини на сторінці **Nodes** мають з'явитися 6 воркерів з адресами `10.x.x.x`.

Чому саме так: n1-standard-1 — це 1 vCPU, як у методичці; Python усе одно однопотоковий.
Master і 6 воркерів — це 7 vCPU. У пробному періоді Google обмежує кількість vCPU, що працюють
одночасно, тож якщо `gcloud` видасть помилку квоти `CPUS`, створи менше воркерів.

---

## Крок 5. Паралельні заміри

1. **Add Job**: Job Name, наприклад `kmp-100mb-w6-r1`; Solution File — `solver_kmp.py`;
   Input File — `data/text_100mb.txt`. Завантаження 100 МБ з дому може тривати кілька хвилин.
2. **Jobs**: дочекайся, поки з'явиться Duration, натисни **Output**. Там будуть
   `matches`, `parallel_time_s`, `total_time_s`, `max_worker_search_s` і рядок для кожного шматка.
   Duration у PARCS показується цілими секундами, тому для звіту бери часи з Output.
3. **Кількість воркерів** змінюй на сторінці **Nodes** кнопкою **Disable/Enable**:
   PARCS роздає роботу лише увімкненим воркерам. Пересоздавати VM не треба.
4. Рекомендована серія: файл 100 МБ, воркерів 1, 2, 3, 4, 5, 6, по 3 запуски кожного
   (18 задач). Для порівняння можна додати ту саму серію на 10 МБ, де накладні витрати
   на пересилання помітніші.
5. Заноси результати у `results/parallel.csv`:

```
text_file,workers,run,matches,read_time_s,parallel_time_s,total_time_s,max_worker_search_s
text_100mb.txt,1,1,...,...,...,...,...
```

Як читати Output: `parallel_time_s` — від роздачі шматків до отримання всіх відповідей
(пересилання тексту + пошук). `max_worker_search_s` — чистий пошук на найповільнішому воркері.
Різниця між ними — накладні витрати на мережу і серіалізацію; це варто показати у звіті.
`matches` має бути однаковим за будь-якої кількості воркерів.

---

## Крок 6. Послідовна базова лінія в хмарі

Умова вимагає тестувати обидва алгоритми в хмарі, тому послідовний KMP міряємо на такій самій
VM (n1-standard-1) і в тому самому контейнері з Python 2.7, що й PARCS. Запускай, коли в PARCS
не виконується жодна задача.

У Cloud Shell:

```bash
git clone https://github.com/vitaliykovtun993/Cloud-Computing-lab1.git && cd Cloud-Computing-lab1
gcloud compute scp kmp.py data_generator.py benchmark_sequential.py master:~
gcloud compute ssh master
```

Далі вже на VM master:

```bash
for f in kmp.py data_generator.py benchmark_sequential.py; do sudo docker cp ~/$f parcs:/tmp/; done
sudo docker exec -w /tmp parcs python data_generator.py --size-mb 100 --pattern-length 12 --insert 1000 --seed 42 -o data/text_100mb.txt
sudo docker exec -w /tmp parcs md5sum data/text_100mb.txt      # має збігтися з certutil з кроку 0.2
sudo docker exec -w /tmp parcs python benchmark_sequential.py data/text_100mb.txt --repeat 3
sudo docker exec -w /tmp parcs cat results/sequential.csv
exit
```

Рядок CSV скопіюй у свій `results/sequential.csv`.
Прискорення для звіту: `S(k) = T_seq / parallel_time_s(k)`, ефективність `E(k) = S(k) / k`.

---

## Крок 7. Прибирання (обов'язково)

Працюючі VM витрачають кредити навіть без навантаження.

```bash
gcloud compute instances delete master worker1 worker2 worker3 worker4 worker5 worker6 --quiet
gcloud compute firewall-rules delete parcs-internal parcs-ui --quiet
```

Або видалити весь проєкт: `gcloud projects delete $PROJECT_ID`. Наприкінці перевір у
**Billing**, що за проєктом нічого не працює.

Якщо робиш перерву на кілька днів, VM можна зупинити:
`gcloud compute instances stop master worker1 ...`. Запуск: `... start ...`. Після старту
master пам'ятає воркерів лише після їх перезапуску (див. нижче).

---

## Якщо щось не працює

| Симптом | Що зробити |
|---|---|
| Сторінка `:8080` не відкривається | Зачекай 2 хв після створення VM; перевір IP у правилі `parcs-ui`; переглянь журнал (нижче) |
| На Nodes немає воркерів | Перезапусти контейнер на воркері: `gcloud compute ssh worker1 --command="sudo docker restart parcs"` |
| На Nodes воркер з адресою `172.17.x.x` | Контейнер узяв адресу docker0 замість `10.x`; напиши мені — замінимо `PARCS_ARGS` на явний конфіг |
| Задача впала (Jobs, червона) | Спершу `python run_solver_local.py <файл>` локально; потім журнал master |
| `Quota 'CPUS' exceeded` / `IN_USE_ADDRESSES` | Створи менше воркерів |
| `ZONE_RESOURCE_POOL_EXHAUSTED` | Інша зона: `gcloud config set compute/zone europe-west1-b` і створи VM заново (правила фаєрволу лишаються) |

Журнали:

```bash
gcloud compute ssh master --command="sudo docker ps -a; sudo docker logs --tail 50 parcs"
gcloud compute ssh master --command="sudo journalctl -u google-startup-scripts.service --no-pager | tail -30"
```

Якщо master перезапускався, воркери треба перезапустити: master тримає список вузлів у пам'яті.

```bash
for w in worker1 worker2 worker3 worker4 worker5 worker6; do gcloud compute ssh $w --command="sudo docker restart parcs"; done
```
