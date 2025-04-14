from app import app

print('Available routes:')
for rule in app.url_map.iter_rules():
    print(f'{rule.endpoint}: {rule.rule}')
