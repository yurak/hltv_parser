import pandas as pd

# Завантажуємо CSV
df = pd.read_csv("../normalization/maps/de_nuke.csv")

opening_mean = df['opening'].mean()

# Функція для присвоєння ролі
def assign_role(row):
    # список значень фіч

    features = ['sniping', 'opening', 'trading', 'entrying', 'utility', 'clutching']
    max_feature = row[features].idxmax()  # яка фіча найбільша
    # умови по пріоритетності
    if row['sniping'] >= 0.7 or max_feature == 'sniping':
        return 'sniper'
    if max_feature in ['entrying', 'utility']:
        return 'support'
    if max_feature in ['trading', 'clutching']:
        return 'lurker'
    if max_feature in [ 'opening']:
        return 'openfragger'
    else:
        return 'unknown'
 
# застосовуємо функцію до всіх рядків
df['role'] = df.apply(assign_role, axis=1)

# Зберігаємо результат
filename = 'de_nuke_with_roles_v2.csv'
df.to_csv(filename, index=False)

print(f"Файл успішно збережено як {filename}")