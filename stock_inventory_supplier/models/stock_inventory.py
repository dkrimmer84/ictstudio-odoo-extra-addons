# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 ICTSTUDIO (<http://www.ictstudio.eu>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class StockInventory(models.Model):
    _inherit = "stock.inventory"

    supplier_id = fields.Many2one(
            comodel_name='res.partner',
            string='Inventoried Supplier',
            readonly=True,
            states={'draft': [('readonly', False)]},
            help="Specify Supplier to focus your inventory on a particular Supplier."
    )

    filter = fields.Selection(
            selection='_selection_filters'
    )

    @api.model
    def _selection_filters(self):
        res_filter = super(StockInventory, self)._selection_filter()
        res_filter.append(('supplier', _('Only Products from Supplier')))
        return res_filter

    @api.model
    def _get_inventory_lines_values(self):
        if self.supplier_id:
            locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
            domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
            args = (tuple(locations.ids),)
            vals = []
            Product = self.env['product.product']
            quant_products = self.env['product.product']
            products_to_filter = self.env['product.product']

            if self.company_id:
                domain += ' AND sq.company_id = %s'
                args += (self.company_id.id,)

            if self.partner_id:
                domain += ' and sq.owner_id = %s'
                args += (self.partner_id.id,)
            if self.lot_id:
                domain += ' and sq.lot_id = %s'
                args += (self.lot_id.id,)
            if self.product_id:
                domain += ' and sq.product_id = %s'
                args += (self.product_id.id,)
            if self.package_id:
                domain += ' and sq.package_id = %s'
                args += (self.package_id.id,)
            if self.category_id:
                categ_products = Product.search([('categ_id', 'child_of', self.category_id.id)])
                domain += ' AND sq.product_id = ANY (%s)'
                args += (categ_products.ids,)
                products_to_filter |= categ_products
            if self.supplier_id:
                # supplier_products = Product.search([('supplier', 'child_of', self.supplier_id)])
                domain += ' and si.name = %s'
                args += (self.supplier_id.id,)
                # products_to_filter |= supplier_products

            self.env.cr.execute('''
                   SELECT sq.product_id as product_id, sum(sq.quantity) as product_qty, sq.location_id as location_id,
                   sq.lot_id as prod_lot_id, sq.package_id as package_id, sq.owner_id as partner_id, si.name as supplier_id
                   FROM stock_quant as sq
                   INNER JOIN product_product as pp on pp.id =  sq.product_id
                   INNER JOIN product_supplierinfo as si on pp.product_tmpl_id = si.product_tmpl_id
                   WHERE''' + domain + '''
                   GROUP BY sq.product_id, sq.location_id, sq.lot_id, sq.package_id, sq.owner_id, si.name
                ''', args)

            for product_data in self.env.cr.dictfetchall():
                for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                    product_data[void_field] = False
                product_data['theoretical_qty'] = product_data['product_qty']
                if product_data['product_id']:
                   product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                   quant_products |= Product.browse(product_data['product_id'])
                vals.append(product_data)
            #if self.exhausted:
            #    exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            #    vals.extend(exhausted_vals)
        else:
            vals = super(StockInventory, self)._get_inventory_lines_values()
        return vals
