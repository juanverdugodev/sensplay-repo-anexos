# Declarando nombre de la aplicación e inicializando, crear la aplicación Flaskp
from app import app

# Importando todos mis Routers (Rutas)
from routers.router_login import *
from routers.router_home import *
from routers.router_page_not_found import *

app.register_blueprint(router_home)

# Ejecutando el objeto Flask
if __name__ == '__main__':
    app.debug = True
    app.run()
