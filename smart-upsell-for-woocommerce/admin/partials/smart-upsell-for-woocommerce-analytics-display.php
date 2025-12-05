<div class="wrap">
    <h1><?php echo esc_html( get_admin_page_title() ); ?></h1>
    <p><?php esc_html_e( 'Here you can see the statistics of your upsell and cross-sell offers.', 'smart-upsell-for-woocommerce' ); ?></p>

    <table class="widefat fixed" cellspacing="0">
        <thead>
            <tr>
                <th class="manage-column column-columnname" scope="col"><?php esc_html_e( 'Metric', 'smart-upsell-for-woocommerce' ); ?></th>
                <th class="manage-column column-columnname" scope="col"><?php esc_html_e( 'Value', 'smart-upsell-for-woocommerce' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><?php esc_html_e( 'Impressions', 'smart-upsell-for-woocommerce' ); ?></td>
                <td><?php echo esc_html( $impressions ); ?></td>
            </tr>
            <tr class="alternate">
                <td><?php esc_html_e( 'Clicks', 'smart-upsell-for-woocommerce' ); ?></td>
                <td><?php echo esc_html( $clicks ); ?></td>
            </tr>
            <tr>
                <td><?php esc_html_e( 'Conversion Rate', 'smart-upsell-for-woocommerce' ); ?></td>
                <td><?php echo esc_html( $conversion_rate ); ?>%</td>
            </tr>
            <tr class="alternate">
                <td><?php esc_html_e( 'Total Revenue', 'smart-upsell-for-woocommerce' ); ?></td>
                <td><?php echo wc_price( $total_revenue ); ?></td>
            </tr>
        </tbody>
    </table>
</div>
