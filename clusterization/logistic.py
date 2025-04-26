import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Зчитування даних
df = pd.read_csv("de_mirage_with_roles_v2.csv")

# 2. Вибираємо ознаки для класифікації

SNIPING = ['sniper_kills_per_round','sniper_kills_percentage','rounds_with_sniper_kills_percentage','sniper_multi_kill_rounds','sniper_opening_kills_per_round']
OPENING = ['opening_kills_per_round','opening_deaths_per_round','opening_attempts','opening_success','win_after_opening_kill','attacks_per_round']
UTILITY = ['utility_damage_per_round','utility_kills_per_100_rounds','flashes_thrown_per_round','flash_assists_per_round','time_opponent_flashed_per_round']
ENTRYING = ['saved_by_teammate_per_round','traded_deaths_per_round','traded_deaths_percentage','opening_deaths_traded_percentage','assists_per_round','support_rounds']
TRADING = ['saved_teammate_per_round','trade_kills_per_round','trade_kills_percentage','assisted_kills_percentage','damage_per_kill']
features = OPENING + SNIPING + UTILITY + ENTRYING + TRADING 
X = df[features]

# 3. Цільова змінна — роль
y = df['role']

# 4. Кодування ролей як чисел
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)  # 0=support, 1=lurker, ...

# 5. Масштабування фіч
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 6. Розбиття на train/test
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_encoded, test_size=0.3, random_state=42)

# 7. Тренування логістичної регресії
model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=500)
model.fit(X_train, y_train)

# 8. Прогноз
y_pred = model.predict(X_test)

# 9. Метрики
print("Classification report:\n", classification_report(y_test, y_pred, target_names=label_encoder.classes_))

# 10. Візуалізація матриці плутанини
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt="d", xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.show()
