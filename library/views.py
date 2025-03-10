from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import requests
from .models import Reservation, Borrowing, Book, BookCopy
from django.db import IntegrityError


def import_book(request):
    if request.method == 'POST':
        isbn = request.POST.get('isbn')
        if not isbn:
            messages.error(request, "Please enter an ISBN.")
            return render(request, 'admin/import_book.html')
        
        # Fetch book data from Google Books API
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['totalItems'] > 0:
                info = data['items'][0]['volumeInfo']
                book_data = {
                    'title': info.get('title', 'Unknown Title'),
                    'author': ', '.join(info.get('authors', ['Unknown Author'])),
                    'isbn': isbn,
                    'publisher': info.get('publisher', 'Unknown Publisher'),
                    'publication_year': info.get('publishedDate', '')[:4] or None
                }
                # Store book data in session for the next step
                request.session['book_data'] = book_data
                return render(request, 'admin/confirm_import.html', {'book_data': book_data})
            else:
                messages.error(request, "No book found for this ISBN.")
        else:
            messages.error(request, "Error contacting the API.")
    return render(request, 'admin/import_book.html')

def confirm_import(request):
    if request.method == 'POST':
        book_data = request.session.get('book_data')
        if not book_data:
            messages.error(request, "Session expired. Please try again.")
            return redirect('import_book')
        
        num_copies = int(request.POST.get('num_copies', 1))
        condition = request.POST.get('condition', 'good')
        
        # Check if book with this ISBN already exists
        book, created = Book.objects.get_or_create(
            isbn=book_data['isbn'],
            defaults={
                'title': book_data['title'],
                'author': book_data['author'],
                'publisher': book_data['publisher'],
                'publication_year': book_data['publication_year']
            }
        )
        
        if not created:
            messages.warning(request, f"Book with ISBN {book_data['isbn']} already exists. Adding copies only.")
        
        # Create BookCopy instances
        for _ in range(num_copies):
            BookCopy.objects.create(
                book=book,
                condition=condition,
                location='L1-A-01'  # Default location; adjust as needed
            )
        
        messages.success(request, f"Added {num_copies} copies of '{book.title}'!")
        return redirect('admin:library_book_changelist')
    
    return redirect('import_book')

def import_books_csv(request):
    if request.method == 'POST':
        csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
        reader = csv.DictReader(csv_file)
        required_fields = ['title', 'author', 'isbn', 'publisher', 'publication_year', 'genre']
        
        if not all(field in reader.fieldnames for field in required_fields):
            messages.error(request, "CSV must contain 'title', 'author', 'isbn', 'publisher', 'publication_year', and 'genre' columns.")
            return render(request, 'admin/import_books_csv.html')
        
        created_count = 0
        for row in reader:
            try:
                book, created = Book.objects.get_or_create(
                    isbn=row['isbn'],
                    defaults={
                        'title': row['title'],
                        'author': row['author'],
                        'publisher': row['publisher'],
                        'publication_year': int(row['publication_year']) if row['publication_year'] else None,
                        'genre': row['genre']
                    }
                )
                if created:
                    created_count += 1
                else:
                    messages.warning(request, f"Book with ISBN {row['isbn']} already exists. Skipping.")
            except KeyError as e:
                messages.error(request, f"Missing field {e} in row for book {row.get('title', 'unknown')}.")
                continue
            except ValueError as e:
                messages.error(request, f"Invalid data in row for book {row.get('title', 'unknown')}: {str(e)}")
                continue
            except Exception as e:
                messages.error(request, f"Error importing book {row.get('title', 'unknown')}: {str(e)}")
                continue
        
        messages.success(request, f"Successfully imported {created_count} books!")
        return redirect('admin:library_book_changelist')
    
    return render(request, 'admin/import_books_csv.html')