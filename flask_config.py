from datetime import timedelta
import os


class Config():
    SECRET_KEY = 'super-secret-string'
    SESSION_COOKIE_SAMESITE  = 'Strict'
    STATIC_FOLDER = None
    STATIC_URL_PATH = None



class DevelopmentConfig(Config):
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000

    @classmethod
    def init_app(cls, app_secret):
        print('Loading Development Config')
        if app_secret:
            cls.SECRET_KEY = app_secret
        if len(app_secret) < 7 or app_secret == 'super_secret_string':
            print('\n*** Your app secret seems insecure, please consider using a randomly generated string ***\n')



class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    HOST = '0.0.0.0'
    PORT = 5000

    @classmethod
    def init_app(cls, app_secret):
        print('Loading Development Config')
        if app_secret:
            cls.SECRET_KEY = app_secret
        if len(app_secret) < 7 or app_secret == 'super_secret_string':
            print('\n*** Your app secret seems insecure, please consider using a randomly generated string ***\n')




class TestingConfig(Config):
    TESTING = True
    HOST = '0.0.0.0'
    PORT = 5000

    @classmethod
    def init_app(cls, app_secret):
        print('Loading Development Config')
        if app_secret:
            cls.SECRET_KEY = app_secret
        if len(app_secret) < 7 or app_secret == 'super_secret_string':
            print('\n*** Your app secret seems insecure, please consider using a randomly generated string ***\n')


flask_configs = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
