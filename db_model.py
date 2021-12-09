import peewee

DB_PROXY = peewee.Proxy()


class BaseModel(peewee.Model):
    class Meta:
        database = DB_PROXY


class User(BaseModel):
    userid = peewee.IntegerField(primary_key=True)
    name = peewee.CharField()
    datum = peewee.DateTimeField()


class UCShoots(BaseModel):
    date = peewee.DateField()
    allianz = peewee.CharField()
    enemy = peewee.CharField()
    player = peewee.ForeignKeyField(User, backref="user")


def create_tables():
    DB_PROXY.create_tables([UCShoots, User])
