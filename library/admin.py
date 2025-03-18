from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from .models import User, Book, BookCopy, Reservation, Borrowing
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django import forms
from django.core.exceptions import ValidationError


class ReservationAdminForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        book = None
        if self.instance.pk and self.instance.book:
            book = self.instance.book
        elif self.data.get('book'):
            try:
                book_id = self.data.get('book')
                book = Book.objects.get(id=book_id)
            except (ValueError, Book.DoesNotExist):
                pass

        if book and not self.instance.copy:
            available_copies = BookCopy.objects.filter(
                book=book,
                status='available'
            )
            if available_copies.exists():
                self.fields['copy'].queryset = available_copies
                self.initial['copy'] = available_copies.first()

    def clean(self):
        cleaned_data = super().clean()
        if 'status' in cleaned_data:
            valid_statuses = dict(self._meta.model.STATUS_CHOICES)
            if cleaned_data['status'] not in valid_statuses:
                raise ValidationError("Invalid status value")
        return cleaned_data

class BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = ('title', 'author', 'isbn', 'publisher', 'publication_year', 'genre')
        import_id_fields = ('isbn',)

class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 1
    fields = ('book', 'condition', 'location')

class BorrowingForm(forms.ModelForm):
    class Meta:
        model = Borrowing
        fields = '__all__'

    def clean_due_date(self):
        if self.instance.pk:
            old_instance = Borrowing.objects.get(pk=self.instance.pk)
            if old_instance.due_date != self.cleaned_data['due_date']:
                if old_instance.renewal_count >= 2:
                    raise forms.ValidationError("Cannot extend due date: Maximum number of renewals (2) reached.")
                if old_instance.return_date is not None:
                    raise forms.ValidationError("Cannot extend due date: Borrowing has been returned.")
        return self.cleaned_data['due_date']

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        if self.instance.pk:  # Only for existing instances
            old_instance = Borrowing.objects.get(pk=self.instance.pk)
            if old_instance.due_date != self.cleaned_data['due_date']:
                # Check if the new due_date extends the old one (assuming renewal intent)
                if self.cleaned_data['due_date'] > old_instance.due_date:
                    try:
                        instance.renew()  # This will handle the increment and save
                    except ValidationError as e:
                        raise forms.ValidationError(str(e))
        instance.save()
        return instance

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role')
    list_filter = ('role',)
    search_fields = ('username', 'email')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role')
        }),
    )
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_users_url'] = '/import-users/'
        return super().changelist_view(request, extra_context)

@admin.register(Book)
class BookAdmin(ImportExportModelAdmin):
    resource_class = BookResource
    list_display = ('title', 'author', 'isbn', 'publication_year', 'genre', 'publisher')
    search_fields = ('title', 'author', 'isbn')
    inlines = [BookCopyInline]

@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ('book', 'condition', 'location', 'status')
    list_filter = ('condition', 'status')
    search_fields = ('book__title', 'location')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    form = ReservationAdminForm
    list_display = ('user', 'book', 'copy', 'reservation_date', 'expiration_date', 'status')
    list_filter = ('status', 'reservation_date')
    search_fields = ('user__username', 'book__title')
    actions = ['cancel_reservations']

    def cancel_reservations(self, request, queryset):
        canceled_count = 0
        for reservation in queryset:
            if reservation.status != 'canceled':
                reservation.cancel()
                canceled_count += 1
        if canceled_count:
            messages.success(request, f"{canceled_count} reservation(s) canceled successfully.")
        else:
            messages.info(request, "No reservations were canceled (already canceled or invalid state).")
    cancel_reservations.short_description = "Cancel selected reservations"

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'copy', 'borrow_date', 'due_date', 'return_date', 'renewal_count')
    list_filter = ('return_date',)
    search_fields = ('user__username', 'copy__book__title')
    form = BorrowingForm
    actions = ['renew_borrowing', 'return_borrowing']

    def renew_borrowing(self, request, queryset):
        renewed = 0
        failed = 0
        for borrowing in queryset:
            try:
                borrowing.renew()
                renewed += 1
            except ValidationError as e:
                failed += 1
                messages.error(request, f"Failed to renew {borrowing}: {str(e)}")
        if renewed:
            messages.success(request, f"Successfully renewed {renewed} borrowing(s).")
        if failed:
            messages.warning(request, f"Failed to renew {failed} borrowing(s).")
    renew_borrowing.short_description = "Renew selected borrowings"

    def return_borrowing(self, request, queryset):
        for borrowing in queryset:
            borrowing.return_book()
            messages.success(request, f"Returned {borrowing.copy}.")
    return_borrowing.short_description = "Return selected borrowings"