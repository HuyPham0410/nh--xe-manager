# Thanh Tinh Bus Management System

This project is currently under development and testing.

## About the Project

Thanh Tinh Bus Management System is a web-based application designed to help manage daily operations for a bus company.

The system focuses on making common tasks easier for employees while providing a simple ticket booking experience for customers.

## Main Features

### Cargo Management
- Add and manage cargo shipments
- Store sender and receiver information
- Track shipping fees
- Track paid and unpaid orders
- Manage delivery locations
- Move waiting cargo to another trip when a bus is full

### Bus Management
- Manage buses
- View bus information
- Assign employees to each bus
- Allow administrators to manage bus schedules

### Employee Management
- Manage drivers and bus assistants
- Assign employees to buses
- Employees can view information related to their assigned work

### Ticket Management
- Sell and manage bus tickets
- Manage passenger information
- Select pickup and drop-off locations
- Manage bus schedules
- Support ticket payments and refunds
- Manage available seats

### Income and Expense Tracking
- Record daily income
- Record expenses with descriptions
- View income and expenses by day, 14 days, or month
- Administrators can view information from all branches

## User Roles

### Admin
Administrators have full access to the management system.

They can manage:
- Cargo
- Buses
- Employees
- Bus schedules
- Tickets
- Income and expenses

### Employee
Employees use a simplified interface for daily tasks.

They can:
- Manage cargo
- Sell tickets
- View bus information
- Record income and expenses related to their work

### Customer
Customers can use the website to:
- Search for available bus trips
- Select pickup and drop-off locations
- Choose available seats
- Book bus tickets

## Technologies

### Frontend
- Next.js
- React
- TypeScript

### Backend
- Python

### Database
- SQLite

The current version uses Python and SQLite for the backend.

Future development may migrate the backend to NestJS and the database to PostgreSQL.

## Requirements

Before running the project, install:

- Node.js 22.12 or newer
- Python 3.11 or newer

## Installation

Clone the repository and install the dependencies:

```bash
npm install
```

Run the initial setup:

```bash
npm run setup
```

## Run the Project

Start both the frontend and backend:

```bash
npm run dev
```

Then open:

```text
http://127.0.0.1:3000
```

Press `Ctrl + C` to stop the application.

## Other Commands

```bash
npm run build
```

Build the Next.js frontend.

```bash
npm start
```

Run the built version locally.

```bash
npm test
```

Run project configuration tests.

```bash
npm run test:smoke
```

Run a basic test for the frontend and backend services.

```bash
npm run typecheck
```

Check the TypeScript frontend.

## Project Status

The project is still under active development.

Current technologies:

**Frontend:** Next.js, React, TypeScript  
**Backend:** Python  
**Database:** SQLite

Planned improvements include:

- Improve the user interface
- Simplify employee workflows
- Improve customer ticket booking
- Add more testing
- Improve security and authentication
- Migrate the backend to NestJS
- Migrate the database to PostgreSQL
- Prepare the application for production deployment

## Project Goal

The goal of this project is to create a practical and easy-to-use management system for a Vietnamese bus company.

Instead of replacing existing workflows with a complicated system, the application is designed to simplify common daily tasks such as cargo management, ticket sales, employee management, vehicle management, and financial tracking.
