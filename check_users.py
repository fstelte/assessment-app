from scaffold import create_app
from scaffold.apps.identity.models import User, UserStatus

app = create_app()

with app.app_context():
    users = User.query.all()
    for user in users:
        print(f"id: {user.id}, username: {user.username}, email: {user.email}, status: {user.status}, status type: {type(user.status)}")

    active_users = User.query.filter(User.status == UserStatus.ACTIVE).all()
    print(f"Active users count: {len(active_users)}")
