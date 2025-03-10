from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import User, Book, BookCopy, Reservation, Borrowing
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django import forms
from django.core.exceptions import ValidationError


class BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = ('title', 'author', 'isbn', 'publisher', 'publication_year', 'genre')
        import_id_fields = ('isbn',)  # ISBN uniquely identifies each book

# Inline for BookCopy within Book
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
    list_display = ('book', 'condition', 'location')
    list_filter = ('condition',)
    search_fields = ('book__title', 'location')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'copy', 'reservation_date', 'expiration_date', 'status')
    list_filter = ('status', 'reservation_date')
    search_fields = ('user__username', 'book__title')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'copy', 'borrow_date', 'due_date', 'return_date', 'renewal_count')
    list_filter = ('return_date',)
    search_fields = ('user__username', 'copy__book__title')
    form = BorrowingForm