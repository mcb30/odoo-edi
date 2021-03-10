"""Groupby tests"""

from odoo.tests import common


class TestGroupby(common.SavepointCase):
    """Tests for groupby method on BaseModel"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_contact_titles()
        cls._setup_contact_categories()
        cls._setup_companies_and_contacts()

    @classmethod
    def create_partner_category(cls, name, **kwargs):
        """Create and return a partner category record with the supplied name"""
        Category = cls.env["res.partner.category"]

        category_vals = {"name": name}
        category_vals.update(kwargs)

        return Category.create(category_vals)

    @classmethod
    def create_partner(cls, name, **kwargs):
        """Create and return a partner record with the supplied name"""
        Partner = cls.env["res.partner"]

        partner_vals = {"name": name}
        partner_vals.update(kwargs)

        return Partner.create(partner_vals)

    @classmethod
    def create_company_partner(cls, name, **kwargs):
        """Create and return a company partner record with the supplied name"""
        company_vals = {"company_type": "company"}
        company_vals.update(kwargs)
        return cls.create_partner(name, **company_vals)

    @classmethod
    def create_contacts_for_partner(cls, partner, no_of_contacts=1, **kwargs):
        """
        Create and return a number (`no_of_contacts`) of partner records and link them to
        supplied partner
        """
        Partner = cls.env["res.partner"]

        contacts = Partner.browse()
        for i in range(no_of_contacts):
            contact_no = i + 1
            contact_name = f"Contact {contact_no}"

            # Set title and category based on whether or not the contact number is even,
            # this is so that the relation fields can be used for grouping
            contact_no_even = contact_no % 2 == 0

            contact_vals = {
                "parent_id": partner.id,
                "title": cls.title_dr.id if contact_no_even else cls.title_prof.id,
                "category_id": [
                    (6, 0, cls.category_even.ids if contact_no_even else cls.category_odd.ids)
                ],
            }
            contact_vals.update(**kwargs)

            contacts += cls.create_partner(contact_name, **contact_vals)

        return contacts

    @classmethod
    def _setup_contact_titles(cls):
        """Create class variables for Dr/Prof titles for use with company contacts"""
        cls.title_dr = cls.env.ref("base.res_partner_title_doctor")
        cls.title_prof = cls.env.ref("base.res_partner_title_prof")

    @classmethod
    def _setup_contact_categories(cls):
        """Create Odd and Even categories for use with company contacts"""
        cls.category_odd = cls.create_partner_category("Odd")
        cls.category_even = cls.create_partner_category("Even")

    @classmethod
    def _setup_companies_and_contacts(cls):
        """Create company partner records as well as contacts linked to each company"""
        cls.company_a = cls.create_company_partner("A")
        cls.company_b = cls.create_company_partner("B")
        cls.company_c = cls.create_company_partner("C")
        cls.all_companies = cls.company_a | cls.company_b | cls.company_c

        contact_count = 3

        cls.company_a_contacts = cls.create_contacts_for_partner(cls.company_a, contact_count)
        cls.company_b_contacts = cls.create_contacts_for_partner(cls.company_b, contact_count)
        cls.company_c_contacts = cls.create_contacts_for_partner(cls.company_c, contact_count)
        cls.all_contacts = cls.company_a_contacts | cls.company_b_contacts | cls.company_c_contacts

    def test_groupby_single_recordset(self):
        """Assert that contacts grouped by a single recordset (`parent_id`) are grouped correctly"""
        contacts_grouped_by_company = self.all_contacts.groupby(lambda c: c.parent_id)

        for company, contacts in contacts_grouped_by_company:
            with self.subTest(company=company, contacts=contacts):
                self.assertEqual(
                    contacts,
                    company.child_ids,
                    f"Company {company.name}'s contacts are: {company.child_ids}, "
                    f"but groupby returned: {contacts}",
                )

    def test_groupby_multiple_recordsets(self):
        """
        Assert that contacts grouped by multiple recordsets (`parent_id`, `title`)
        are grouped correctly
        """
        expected_groupby_results = {}

        for company in self.all_companies:
            for contact in company.child_ids:
                # Add contact to expected groupby results for this company and title
                company_title_key = (company, contact.title)

                if company_title_key in expected_groupby_results:
                    expected_groupby_results[company_title_key] += contact
                else:
                    expected_groupby_results[company_title_key] = contact

        contacts_grouped_by_company_and_title = self.all_contacts.groupby(
            lambda c: (c.parent_id, c.title)
        )

        for groupby_key, contacts in contacts_grouped_by_company_and_title:
            with self.subTest(groupby_key=groupby_key):
                company, title = groupby_key
                expected_contacts = expected_groupby_results[groupby_key]
                self.assertEqual(
                    contacts,
                    expected_contacts,
                    f"Company {company.name} & Title {title.name} "
                    f"should have returned: {expected_contacts}, got: {contacts}",
                )

    def test_groupby_recordset_and_tuple_with_multiple_recordsets(self):
        """
        Assert that contacts grouped by a recordset and a tuple of multiple recordsets
        (`parent_id`, (`title`, 'category_id')) are grouped correctly
        """
        expected_groupby_results = {}

        for company in self.all_companies:
            for contact in company.child_ids:
                # Add contact to expected groupby results for this company and (title and category)
                company_title_category_key = (company, (contact.title, contact.category_id))

                if company_title_category_key in expected_groupby_results:
                    expected_groupby_results[company_title_category_key] += contact
                else:
                    expected_groupby_results[company_title_category_key] = contact

        contacts_grouped_by_company_and_title = self.all_contacts.groupby(
            lambda c: (c.parent_id, (c.title, c.category_id))
        )

        for groupby_key, contacts in contacts_grouped_by_company_and_title:
            with self.subTest(groupby_key=groupby_key):
                company = groupby_key[0]
                title, category = groupby_key[1]
                expected_contacts = expected_groupby_results[groupby_key]
                self.assertEqual(
                    contacts,
                    expected_contacts,
                    f"Company {company.name} & (Title {title.name} & Category: {category.name}) "
                    f"should have returned: {expected_contacts}, got: {contacts}",
                )
