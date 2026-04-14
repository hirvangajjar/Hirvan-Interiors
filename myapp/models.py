from django.db import models
from django.utils.text import slugify
import uuid
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import cloudinary.uploader

class User(models.Model):
    name = models.CharField(max_length=40)
    email=models.EmailField(unique=True)
    contact=models.BigIntegerField()
    password = models.CharField(max_length=20)
    usertype = models.CharField(max_length=26)
    uprofile = models.ImageField(upload_to='user_profiles/', null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)

    @property
    def image_url(self):
        if self.uprofile and hasattr(self.uprofile, 'url'):
            return self.uprofile.url
        else:
            return "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSnSSxXHLqu5lsHYkFlZkvXuo2ZamNvdqLiCg&s"

    def __str__(self):
        return f"{self.name}"
    

class Designer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = (
        ('residential', 'residential'),
        ('commercial', 'commercial'),
    )
    dcategory = models.CharField(max_length=30, choices=category)
    dname = models.CharField(max_length=30)
    dstartprice = models.IntegerField()
    dsummary = models.TextField()
    dimage = models.ImageField(upload_to='interior')
    dimage2 = models.ImageField(upload_to='interior', null=True, blank=True)
    dimage3 = models.ImageField(upload_to='interior', null=True, blank=True)
    slug = models.SlugField(unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.dname}"
    
    @property
    def project_code(self):
        return f"ARC-{self.id:04d}"
    
    class Meta:
        unique_together = [['user', 'dname']]

        verbose_name = "Interior Project"
        verbose_name_plural = "Interior Projects"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.dname)
            if Designer.objects.filter(slug=base_slug).exists():
                self.slug = f"{base_slug}-{str(uuid.uuid4())[:4]}"
            else:
                self.slug = base_slug
        super().save(*args, **kwargs)


class Moodboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    design = models.ForeignKey(Designer, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'design']]

class Site(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sites')
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    site_type = models.CharField(max_length=50, choices=[
        ('Residential', 'Residential'),
        ('Commercial', 'Commercial')
    ], default='Residential')
    visit_date = models.DateField(null=True, blank=True)
    visit_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.name}'s Site in {self.city}"

class Booking(models.Model):
    dreamer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    designer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    design = models.ForeignKey(Designer, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    order_id = models.CharField(max_length=100, unique=True) 
    payment_session_id = models.CharField(max_length=255, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.order_id} - {self.is_paid}"
    

@receiver(pre_delete, sender=User)
def delete_user_image(sender, instance, **kwargs):
    if instance.uprofile:
        try:
            cloudinary.uploader.destroy(instance.uprofile.name)
            print(f"SUCCESS: Profile picture for {instance.email} destroyed!")
        except Exception as e:
            print(f"FAILED to delete profile picture: {e}")

@receiver(pre_delete, sender=Designer)
def delete_designer_images(sender, instance, **kwargs):
    images_to_delete = [instance.dimage, instance.dimage2, instance.dimage3]
    
    for img in images_to_delete:
        if img: 
            try:
                cloudinary.uploader.destroy(img.name)
                print(f"SUCCESS: {img.name} destroyed from Cloudinary!")
            except Exception as e:
                print(f"FAILED to delete project image: {e}")
