from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="category_images/", blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="menu_images/", blank=True, null=True)
    tagline = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"
