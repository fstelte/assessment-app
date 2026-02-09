from ...templates.navigation import NavEntry


def register(app):
    from .routes import maturity_bp
    app.register_blueprint(maturity_bp)


NAVIGATION = [
    NavEntry(endpoint="maturity.index", label="maturity.nav.label", icon="chart-bar", order=50)
]
