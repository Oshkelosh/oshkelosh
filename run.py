from app import create_app

app = create_app()

if __name__ == '__main__':
    if app:
        app.run(host=app.config['HOST'], port=app.config['PORT'])
