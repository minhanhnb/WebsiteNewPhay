from models.Momo_User import MomoUser

def insert_Cash_Momo_User(name, cash):
    """
    Wrapper function to call model insertCash.
    This keeps routes cleaner.
    """
    return MomoUser.insertCash(name, cash)

def withdraw_Cash(name,cash):
    return MomoUser.withdrawCash(name,cash)


def get_all_Cash():
    return MomoUser.get_all_cash()

