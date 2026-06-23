def redirect_by_role(user):

    if user.role == 'customer':
        return 'customer_dashboard'

    elif user.role == 'worker':
        return 'furniture_dashboard'

    elif user.role == 'manager':
        return 'manager_dashboard'

    elif user.role == 'admin':
        return 'admin_dashboard'

    return 'home'