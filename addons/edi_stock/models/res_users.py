from odoo import models

class Users(models.Model):
    
    _inherit = "res.users"

    def get_current_user_id(self):
        """
        Returns the current user id.  
        """
        return self.env.uid
