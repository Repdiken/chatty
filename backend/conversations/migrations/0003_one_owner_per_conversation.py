from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversations", "0002_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="conversationmember",
            constraint=models.UniqueConstraint(
                condition=models.Q(role="owner"),
                fields=("conversation",),
                name="one_owner_per_conversation",
            ),
        ),
    ]
