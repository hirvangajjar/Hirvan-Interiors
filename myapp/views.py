from django.shortcuts import render,redirect
from django.contrib import messages
from .models import *
from django.conf import settings
from django.core.mail import send_mail
import random
import time
import uuid
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta
from django.http import JsonResponse
from django.db import IntegrityError
import json
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
from datetime import datetime,date
from django.contrib import auth
import cloudinary.uploader
cashfree_instance = Cashfree(
    XClientId=settings.CASHFREE_CLIENT_ID,
    XClientSecret=settings.CASHFREE_CLIENT_SECRET,
    XEnvironment=Cashfree.SANDBOX 
)



def index(request):
    if 'email' in request.session:
        return redirect('home')
    return render(request,'index.html')

def about(request):
    return render(request,'about.html')

def contact(request):
    return render(request,'contact.html')

def feature(request):
    return render(request,'feature.html')

def project(request):
    return render(request,'project.html')

def service(request):
    return render(request,'service.html')

def team(request):
    return render(request,'team.html')

def testimonial(request):
    return render(request,'testimonial.html')

def signup(request):
    if request.method == "POST":
        try:
            user = User.objects.get(email=request.POST['email'])
            messages.error(request,"User already Exists !")
            return render(request,'sign-up.html')
        except User.DoesNotExist:
            if request.POST['password'] == request.POST['cpassword']:
                u_type = request.POST.get('usertype')
                fee = request.POST.get('cf')
                if not fee or u_type == "Dreamer":
                    fee = 0
                
                User.objects.create(
                    name=request.POST['name'],
                    email=request.POST['email'],
                    password=request.POST['password'],
                    contact=request.POST['contact'],
                    consultation_fee=fee, 
                    usertype=u_type
                )
                messages.success(request, "Sign-Up Successful !")
                return redirect ('login')
            else:
                messages.error(request, "Password and Confirm Password do not Match !")
                return render(request, 'sign-up.html')
    else:
        return render (request,'sign-up.html')
    

def login(request):
    if request.method == "POST":
        try:
            user = User.objects.get(email = request.POST['email'])
            if user.password == request.POST['password']:
                request.session['email'] = user.email
                request.session['usertype'] = user.usertype
                if user.uprofile:
                    request.session['profile'] = user.uprofile.url
                else:
                    request.session['profile'] = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSnSSxXHLqu5lsHYkFlZkvXuo2ZamNvdqLiCg&s"
        
                messages.success(request,"Login Successful !")
                return redirect('home')
            else:
                messages.error(request, "Incorrect Credentials !")
                return render (request,'login.html')
        except User.DoesNotExist:
            messages.error(request,"Account Does not Exists !")
            return render(request,'login.html')
    else:
        return render (request,'login.html')

def logout(request):
    reason = request.GET.get('reason')
    auth.logout(request)
    request.session.flush()
    if reason == 'expired':
        messages.warning(request, "Your session expired due to Inactivity !")
    else:
        messages.success(request, "Logged out Successfully !")
    return redirect('login')

def fpass(request):
    if request.method == "POST":
        try:
            user = User.objects.get(email = request.POST['email'])
            subject = 'OTP for Forgotten-Password !'
            otp = random.randint(111111,999999)
            msg = 'Hi ' + user.name + ', Your OTP is : ' + str(otp) + '.' 
            email_from = settings.EMAIL_HOST_USER
            recepient_list = [user.email]
            try:
                send_mail(subject, msg, email_from, recepient_list, fail_silently=False)
            except Exception as e:
                print(f"EMAIL FAILED: {e}") 
                messages.error(request, 'Network error ! Please try again in a few minutes !')
                return redirect('fpass')

            request.session['resetpass_email'] = user.email
            request.session['otp'] = otp
            request.session['otp_timestamp'] = time.time()

            messages.success(request,'OTP sent Successfully !')
            return redirect ('otp')
        except User.DoesNotExist:
            messages.error(request,'Email does not Exist !')
            return render(request,'forgot-password.html')
    else:
        return render(request,'forgot-password.html')


def otp(request):

    if 'resetpass_email' not in request.session:
        messages.error(request, "Please enter your email First !")
        return redirect('fpass')
    
    created_time = request.session.get('otp_timestamp', 0)
    current_time = time.time()
    elapsed_time = int(current_time - created_time)
    seconds_left = max(0, 60 - elapsed_time) 

    if request.method == "POST":
        try:
            saved_otp = request.session.get('otp')
            user_otp = request.POST.get('uotp') 

            if seconds_left <= 0:
                messages.error(request, "OTP Expired !")
                return render(request, 'otp.html', {'seconds_left': 0}) 
            
            if saved_otp and user_otp and int(saved_otp) == int(user_otp):
                del request.session['otp'] 
                messages.success(request, "OTP Verified !")
                return redirect('newpass')
            
            else:
                messages.error(request, 'Invalid OTP !')
                return render(request, 'otp.html', {'seconds_left': seconds_left})
        
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid Number !')
            return render(request, 'otp.html', {'seconds_left': seconds_left})

    return render(request, 'otp.html', {'seconds_left': seconds_left})

def resend_otp(request):
    if 'resetpass_email' not in request.session:
        messages.error(request, "Please enter your email First !")
        return redirect('fpass')
    
    email = request.session.get('resetpass_email')
    
    if email:
        try:
            user = User.objects.get(email=email)
            new_otp = random.randint(111111, 999999)
            request.session['otp'] = new_otp
            request.session['otp_timestamp'] = time.time() 

            subject = 'New OTP for Forgotten-Password !'
            msg = f'Hi {user.name}, Your NEW OTP is : {new_otp}.'
            email_from = settings.EMAIL_HOST_USER
            send_mail(subject, msg, email_from, [user.email])
            
            messages.success(request, "A new OTP has been Sent !")
            return redirect('otp')
            
        except User.DoesNotExist:
            messages.error(request, "User account Error !")
            return redirect('fpass')
    else:
        messages.error(request, "Session expired. Please enter your email Again !")
        return redirect('fpass')

def newpass(request):
    if 'resetpass_email' not in request.session:
        messages.error(request, "Please enter your email First !")
        return redirect('fpass')
    
    if request.method == "POST":
        np = request.POST.get('npass')
        cnp = request.POST.get('cnpass')
        
        if np == cnp:
            try:
                user = User.objects.get(email=request.session['resetpass_email'])
                user.password = np  
                user.save()

                request.session.flush() 
                
                messages.success(request, "Password reset Successfull ! Please login !")
                return redirect('login')
                
            except User.DoesNotExist:
                messages.error(request, "User not Found ! Please try Again !")
                return redirect('fpass')
        else:
            messages.error(request, "Passwords do not Match !")
            return render(request, 'new-password.html')

    return render(request, 'new-password.html')


def uprofile(request):
    user = User.objects.get(email=request.session['email'])
    
    if request.method == "POST":
        user.name = request.POST['name']
        user.contact = request.POST['mobile']
        
        if user.usertype == "designer":
            fee = request.POST.get('cf')
            if fee: 
                user.consultation_fee = fee

        if 'uprofile' in request.FILES:
            if user.uprofile:
                try:
                    cloudinary.uploader.destroy(user.uprofile.name)
                except Exception as e:
                    print(f"Cloudinary delete failed: {e}")

            user.uprofile = request.FILES['uprofile'] 

        elif request.POST.get('remove_image_flag') == "true":
            if user.uprofile:
                try:
                    cloudinary.uploader.destroy(user.uprofile.name)
                except Exception as e:
                    print(f"Cloudinary delete failed: {e}")
                
            user.uprofile = None
            request.session['profile'] = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSnSSxXHLqu5lsHYkFlZkvXuo2ZamNvdqLiCg&s"

        user.save()
        
        if user.uprofile:
            request.session['profile'] = user.uprofile.url

        messages.success(request, "Profile Updated Successfully !")
        return redirect('uprofile')
        
    else:   
        return render(request, 'uprofile.html', {'user': user}) 
    
def changepass(request):
    user = User.objects.get(email = request.session['email'])
    if request.method == "POST":
        try:
            if user.password == request.POST['opass']:
                if request.POST['npass'] == request.POST['cnpass']:
                    user.password = request.POST['npass']
                    user.save()
                    messages.success(request,"Password Updated Successfully !")
                    return redirect("uprofile")
                else:
                    messages.error(request,"New Password and Confirm New Password does not Match ! ")
                    return render(request, 'changepass.html')
            else:
                messages.error(request,"Old Password is Incorrect !")
                return render(request, 'changepass.html')
        except:
            pass
    else:
        return render(request, 'changepass.html')
    

def add_design(request):
    user = User.objects.get(email = request.session['email'])
    if request.method == "POST":
        try:
            Designer.objects.create(
                user=user,
                dname=request.POST['dname'],
                dcategory=request.POST['dcategory'],
                dstartprice=request.POST['dprice'],
                dsummary=request.POST['dsummary'],
                dimage=request.FILES['dimage'],
                dimage2=request.FILES.get('dimage2'), 
                dimage3=request.FILES.get('dimage3')
            )
            messages.success(request, "Design added Successfully !")
            return redirect('manage_design')
        
        except IntegrityError:
            messages.error(request,f"You already have a design named '{request.POST['dname']}'. Please use a unique Name !")
            return render(request, 'add_design.html') 
            
    return render(request, 'add_design.html')

def manage_design(request):
    user = User.objects.get(email = request.session['email'])
    designer = Designer.objects.filter(user = user)

    return render(request,'manage_design.html',{'designer' : designer})

def edit_design(request, pk):
    try:
        user = User.objects.get(email=request.session['email'])
        design = Designer.objects.get(id=pk, user=user) 
    except (User.DoesNotExist, Designer.DoesNotExist):
        messages.error(request, "Design not Found !")
        return redirect('manage_design')

    if request.method == "POST":
        design.dname = request.POST['dname']
        design.dstartprice = request.POST['dprice']
        design.dsummary = request.POST['dsummary']
        
        if request.FILES.get('dimage'):
            if design.dimage:
                try:
                    cloudinary.uploader.destroy(design.dimage.name)
                except Exception as e:
                    print(f"Cloudinary delete failed: {e}")
            design.dimage = request.FILES.get('dimage')
            
        if request.FILES.get('dimage2'):
            if design.dimage2:
                try:
                    cloudinary.uploader.destroy(design.dimage2.name)
                except Exception as e:
                    print(f"Cloudinary delete failed: {e}")
            design.dimage2 = request.FILES.get('dimage2')
            
        if request.FILES.get('dimage3'):
            if design.dimage3:
                try:
                    cloudinary.uploader.destroy(design.dimage3.name)
                except Exception as e:
                    print(f"Cloudinary delete failed: {e}")
            design.dimage3 = request.FILES.get('dimage3')

        design.save()
        messages.success(request, "Design Updated Successfully !")
        return redirect('edit_design', pk=design.id) 
    
    else:   
        return render(request, 'edit_design.html', {'design': design})
    

def delete_design(request, pk):
    try:
        user = User.objects.get(email=request.session['email'])
        design = Designer.objects.get(id=pk, user=user) 
        design.delete() 
        
        messages.success(request, "Design and all associated files Deleted !")
        return redirect('manage_design') 
        
    except (User.DoesNotExist, Designer.DoesNotExist):
        messages.error(request, "Design not Found !")
        return redirect('manage_design')
    
def home(request):
    if 'email' not in request.session:
        return redirect('login')
    else:
        context = {}
        context['all_designs'] = Designer.objects.all().order_by('-id')[:6] 
    
        user_design_count = 0
        try:
            user = User.objects.get(email=request.session['email'])
            context['user'] = user
            user_design_count = Designer.objects.filter(user=user).count()
            total_design_count = Designer.objects.count()
            design = Designer.objects.all()
        except User.DoesNotExist:
            pass
    context['my_count'] = user_design_count
    context['total_count'] = total_design_count
    context['design'] = design

    return render(request, 'home.html', context)

def design_info(request, design_slug):
    if 'email' not in request.session:
        messages.error(request, "Please login to view project Details !")
        return redirect('login')

    try:
        user = User.objects.get(email=request.session['email'])
        design = Designer.objects.get(slug=design_slug)
        
        return render(request, 'design_info.html', {
            'design': design,
            'user': user 
        })
        
    except User.DoesNotExist:
        return redirect('logout') 
    except Designer.DoesNotExist:
        messages.error(request, "The requested design does not Exist !")
        return redirect('home')
    
def moodboard_add(request, pk):
    if 'email' not in request.session:
        messages.error(request, "Please login to add designs to your Moodboard !")
        return redirect('login')

    try:
        user = User.objects.get(email=request.session['email'])
        design = Designer.objects.get(id=pk) 
        obj, created = Moodboard.objects.get_or_create(user=user, design=design)

        if created:
            messages.success(request, "Added to your Moodboard !")
        else:
            messages.info(request, "This design is already in your Moodboard !")
        return redirect('design_info', design_slug=design.slug)
        
    except Designer.DoesNotExist:
        messages.error(request, "Design not Found !")
        return redirect('home')
    
def moodboard(request):
    if 'email' not in request.session:
        return redirect('login')

    try:
        user = User.objects.get(email=request.session['email'])
        design = Moodboard.objects.filter(user=user).select_related('design')

        return render(request, 'moodboard.html', {'design': design})
        
    except User.DoesNotExist:
        return redirect('logout')
    

def moodboard_delete(request, pk):
    
    if 'email' not in request.session:
        return redirect('login')
        
    try:
        user = User.objects.get(email=request.session['email'])
        item = get_object_or_404(Moodboard, id=pk, user=user)
        item.delete()
        messages.success(request, "Design removed from your Moodboard !")
        
    except User.DoesNotExist:
        request.session.flush() 
        return redirect('login')
    except Exception as e:
        messages.error(request, "Something went wrong while removing the Item !")
        
    return redirect('moodboard')



    
def designer_info(request, pk):
    if 'email' not in request.session:
        return redirect('login')
    
    try:
        project = Designer.objects.get(id=pk)
        designer = project.user 
        
        return render(request, 'designer_info.html', {
            'designer': designer,
            'project': project
        })

    except Designer.DoesNotExist:
        messages.error(request, "Project not Found !")
        return redirect('home')
    
def create_cashfree_booking(request, pk):
    if 'email' not in request.session:
        return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
    if request.method == "POST":
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        design = get_object_or_404(Designer, id=pk)
        user = User.objects.get(email=request.session['email'])

        visit_date_str = data.get('visit_date')
        visit_time_str = data.get('visit_time')
        if visit_date_str and visit_time_str:
            selected_date = datetime.strptime(visit_date_str, '%Y-%m-%d').date()
            selected_time = datetime.strptime(visit_time_str, '%H:%M').time()
        
            now = datetime.now()
            if selected_date < now.date():
                return JsonResponse({'error': 'You cannot book a date in the past.'}, status=400)
            if selected_date == now.date() and selected_time < now.time():
                    return JsonResponse({'error': 'This time slot has already passed for today.'}, status=400)
            if selected_time.hour < 10 or selected_time.hour >= 18:
                return JsonResponse({'error': 'Please select a time between 10:00 AM and 06:00 PM.'}, status=400)

        new_site = Site.objects.create(
        user=user,
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        pincode=data.get('pincode'),
        site_type=data.get('site_type'),
        visit_date=selected_date,     
        visit_time=selected_time  
        )
        unique_order_id = f"INS_{uuid.uuid4().hex[:12]}"
        clean_phone = str(user.contact)[-10:]
        clean_amount = round(float(design.user.consultation_fee), 2)

        customer = CustomerDetails(
            customer_id=f"USER_{user.id}", 
            customer_phone=clean_phone, 
            customer_email=user.email
        )

        return_url = request.build_absolute_uri(
            reverse("payment_success")
        ) + f"?order_id={unique_order_id}"

        meta = OrderMeta(return_url=return_url)

        order_request = CreateOrderRequest(
            order_id=unique_order_id,
            order_amount=clean_amount,
            order_currency="INR",
            customer_details=customer,
            order_meta=meta
        )

        try:
            api_response = cashfree_instance.PGCreateOrder("2023-08-01", order_request)
            if not api_response.data or not api_response.data.payment_session_id:
                return JsonResponse({"error": "Failed to create payment session"}, status=400)
            payment_session_id = api_response.data.payment_session_id
            
            Booking.objects.create(
                dreamer=user,
                designer=design.user,
                design=design,
                site=new_site,
                amount=design.user.consultation_fee,
                order_id=unique_order_id,
                payment_session_id=payment_session_id
            )

            return JsonResponse({
                'payment_session_id': payment_session_id,
                'order_id': unique_order_id
            })

        except Exception as e :
            return JsonResponse({'error': str(e)}, status=400)

def payment_success(request):

    if 'email' not in request.session:
        return redirect('login')
    order_id = request.GET.get('order_id')
    
    try:
        api_response = cashfree_instance.PGFetchOrder("2023-08-01", order_id)
        if api_response.data and api_response.data.order_status == "PAID":
            booking = Booking.objects.get(order_id=order_id)
            booking.is_paid = True
            booking.save()
            return render(request, 'success.html', {'booking': booking})
        else:
            return redirect('payment_failure') 
            
    except :
        return redirect('payment_failure')
def payment_failure(request):
    return render(request, 'failure.html')

def download_receipt(request, order_id):
    if 'email' not in request.session:
        return redirect('login')
    booking = get_object_or_404(Booking, order_id=order_id)
    template_path = 'receipt_pdf.html'
    context = {'booking': booking}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Receipt_{order_id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

def bookings(request):
    if 'email' not in request.session:
        return render('login')
    try:
        user = User.objects.get(email = request.session['email'])
        user_bookings = Booking.objects.filter(dreamer=user).order_by('-id')

        return render(request, 'bookings.html', {
            'bookings': user_bookings,
        })
    except User.DoesNotExist:
        return redirect('login')
    
def appointments(request):
    if 'email' not in request.session:
        return redirect('login')
    
    user = User.objects.get(email=request.session['email'])
    appointments = Booking.objects.filter(designer=user, is_paid=True).order_by('-id')

    return render(request, 'appointments.html', {
        'appointments': appointments
    })

    
    








                    




            

    
            

