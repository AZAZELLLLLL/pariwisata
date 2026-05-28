import os

import app as app_module


if __name__ == '__main__':
    app_module.app.run(
        host='127.0.0.1',
        port=int(os.getenv('PORT', '5000')),
        debug=False,
        use_reloader=False
    )
