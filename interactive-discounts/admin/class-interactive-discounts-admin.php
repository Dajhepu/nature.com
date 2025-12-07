<?php
class Interactive_Discounts_Admin {

    private $plugin_name;
    private $version;
    private $options;

    public function __construct( $plugin_name, $version ) {
        $this->plugin_name = $plugin_name;
        $this->version = $version;
    }

    public function enqueue_styles() {
        wp_enqueue_style( 'wp-color-picker' );
        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'css/interactive-discounts-admin.css', array(), $this->version, 'all' );
    }

    public function enqueue_scripts() {
        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'js/interactive-discounts-admin.js', array( 'jquery', 'wp-color-picker' ), $this->version, true );
    }

    public function add_options_page() {
        add_menu_page(__( 'Interactive Discounts Settings', 'interactive-discounts' ), __( 'Discount Games', 'interactive-discounts' ), 'manage_options', 'interactive-discounts-settings', array( $this, 'create_admin_page' ), 'dashicons-games');

        add_submenu_page(
            'interactive-discounts-settings',
            __( 'Collected Emails', 'interactive-discounts' ),
            __( 'Collected Emails', 'interactive-discounts' ),
            'manage_options',
            'interactive-discounts-emails',
            array( $this, 'create_emails_page' )
        );
    }

    public function create_admin_page() {
        $this->options = get_option( 'id_wheel_settings' );
        ?>
        <div class="wrap">
            <h1><?php echo esc_html( get_admin_page_title() ); ?></h1>
            <form method="post" action="options.php">
            <?php
                settings_fields( 'id_wheel_option_group' );
                do_settings_sections( 'interactive-discounts-admin' );
                submit_button();
            ?>
            </form>
        </div>
        <?php
    }

    public function create_emails_page() {
        require_once plugin_dir_path( __FILE__ ) . 'class-interactive-discounts-emails-list-table.php';
        $emails_table = new Interactive_Discounts_Emails_List_Table();
        ?>
        <div class="wrap">
            <h1 class="wp-heading-inline"><?php echo esc_html( get_admin_page_title() ); ?></h1>
            <form method="post">
                <?php
                $emails_table->prepare_items();
                $emails_table->display();
                ?>
            </form>
        </div>
        <?php
    }

    public function page_init() {
        register_setting('id_wheel_option_group', 'id_wheel_settings', array( $this, 'sanitize' ));

        // Wheel Settings Section
        add_settings_section('wheel_settings_section', __( 'Wheel of Fortune Settings', 'interactive-discounts' ), null, 'interactive-discounts-admin');
        add_settings_field('enable_wheel', __( 'Enable Wheel', 'interactive-discounts' ), array( $this, 'enable_wheel_callback' ), 'interactive-discounts-admin', 'wheel_settings_section');
        add_settings_field('segments', __( 'Wheel Segments', 'interactive-discounts' ), array( $this, 'segments_callback' ), 'interactive-discounts-admin', 'wheel_settings_section');

        // Email Collection Section
        add_settings_section('email_collection_section', __( 'Email Collection Settings', 'interactive-discounts' ), null, 'interactive-discounts-admin');
        add_settings_field('enable_email_collection', __( 'Enable Email Collection', 'interactive-discounts' ), array( $this, 'enable_email_collection_callback' ), 'interactive-discounts-admin', 'email_collection_section');
        add_settings_field('email_title', __( 'Form Title', 'interactive-discounts' ), array( $this, 'email_title_callback' ), 'interactive-discounts-admin', 'email_collection_section');
        add_settings_field('email_subtitle', __( 'Form Subtitle', 'interactive-discounts' ), array( $this, 'email_subtitle_callback' ), 'interactive-discounts-admin', 'email_collection_section');
        add_settings_field('email_button_text', __( 'Button Text', 'interactive-discounts' ), array( $this, 'email_button_text_callback' ), 'interactive-discounts-admin', 'email_collection_section');
    }

    public function sanitize( $input ) {
        $new_input = array();
        if( isset( $input['enable_wheel'] ) ) $new_input['enable_wheel'] = absint( $input['enable_wheel'] );
        if( isset( $input['enable_email_collection'] ) ) $new_input['enable_email_collection'] = absint( $input['enable_email_collection'] );
        if( isset( $input['email_title'] ) ) $new_input['email_title'] = sanitize_text_field( $input['email_title'] );
        if( isset( $input['email_subtitle'] ) ) $new_input['email_subtitle'] = sanitize_text_field( $input['email_subtitle'] );
        if( isset( $input['email_button_text'] ) ) $new_input['email_button_text'] = sanitize_text_field( $input['email_button_text'] );

        if( isset( $input['segments'] ) ) {
             $new_input['segments'] = array_map( function($segment) {
                return [
                    'text'      => sanitize_text_field($segment['text']), 'type'      => sanitize_text_field($segment['type']),
                    'value'     => sanitize_text_field($segment['value']), 'fillStyle' => sanitize_hex_color($segment['fillStyle']),
                ];
             }, $input['segments']);
        }
        return $new_input;
    }

    public function enable_wheel_callback() {
        printf('<input type="checkbox" id="enable_wheel" name="id_wheel_settings[enable_wheel]" value="1" %s /> <label for="enable_wheel">%s</label>',
            isset( $this->options['enable_wheel'] ) && $this->options['enable_wheel'] == 1 ? 'checked' : '', esc_html__( 'Enable the Wheel of Fortune popup on your site.', 'interactive-discounts' ));
    }

    // Callbacks for Email Collection
    public function enable_email_collection_callback() {
        printf('<input type="checkbox" id="enable_email_collection" name="id_wheel_settings[enable_email_collection]" value="1" %s /> <label for="enable_email_collection">%s</label>',
            isset( $this->options['enable_email_collection'] ) && $this->options['enable_email_collection'] == 1 ? 'checked' : '', esc_html__( 'Ask for user\'s email before spinning the wheel.', 'interactive-discounts' ));
    }
    public function email_title_callback() {
        printf('<input type="text" id="email_title" name="id_wheel_settings[email_title]" value="%s" />',
            isset( $this->options['email_title'] ) ? esc_attr( $this->options['email_title']) : __( 'Want a Discount?', 'interactive-discounts' ));
    }
    public function email_subtitle_callback() {
        printf('<input type="text" id="email_subtitle" name="id_wheel_settings[email_subtitle]" value="%s" />',
            isset( $this->options['email_subtitle'] ) ? esc_attr( $this->options['email_subtitle']) : __( 'Enter your email to spin the wheel!', 'interactive-discounts' ));
    }
    public function email_button_text_callback() {
        printf('<input type="text" id="email_button_text" name="id_wheel_settings[email_button_text]" value="%s" />',
            isset( $this->options['email_button_text'] ) ? esc_attr( $this->options['email_button_text']) : __( 'Try my luck!', 'interactive-discounts' ));
    }


    public function segments_callback() {
        $segments = ( isset( $this->options['segments'] ) && is_array($this->options['segments']) ) ? $this->options['segments'] : [];
        ?>
        <div id="segment_repeater">
            <?php foreach ( $segments as $index => $segment ) : ?>
            <div class="segment-row">
                <input type="text" name="id_wheel_settings[segments][<?php echo $index; ?>][text]" value="<?php echo esc_attr( $segment['text'] ); ?>" placeholder="<?php esc_attr_e( 'Segment Text', 'interactive-discounts' ); ?>" />
                <select name="id_wheel_settings[segments][<?php echo $index; ?>][type]">
                    <option value="none" <?php selected( $segment['type'], 'none' ); ?>><?php esc_html_e( 'No Prize', 'interactive-discounts' ); ?></option>
                    <option value="percentage" <?php selected( $segment['type'], 'percentage' ); ?>><?php esc_html_e( 'Percentage Discount', 'interactive-discounts' ); ?></option>
                    <option value="fixed_cart" <?php selected( $segment['type'], 'fixed_cart' ); ?>><?php esc_html_e( 'Fixed Cart Discount', 'interactive-discounts' ); ?></option>
                </select>
                <input type="text" name="id_wheel_settings[segments][<?php echo $index; ?>][value]" value="<?php echo esc_attr( $segment['value'] ); ?>" placeholder="<?php esc_attr_e( 'Value (e.g., 10)', 'interactive-discounts' ); ?>" />
                <input type="text" name="id_wheel_settings[segments][<?php echo $index; ?>][fillStyle]" value="<?php echo esc_attr( $segment['fillStyle'] ); ?>" class="color-picker" />
                <button type="button" class="button remove_segment_button"><?php esc_html_e( 'Remove', 'interactive-discounts' ); ?></button>
            </div>
            <?php endforeach; ?>
        </div>
        <button type="button" id="add_segment_button" class="button"><?php esc_html_e( 'Add Segment', 'interactive-discounts' ); ?></button>
        <div class="segment-row segment-template" style="display:none;">
            <input type="text" name="id_wheel_settings[segments][][text]" value="" placeholder="<?php esc_attr_e( 'Segment Text', 'interactive-discounts' ); ?>" />
            <select name="id_wheel_settings[segments][][type]">
                <option value="none"><?php esc_html_e( 'No Prize', 'interactive-discounts' ); ?></option>
                <option value="percentage"><?php esc_html_e( 'Percentage Discount', 'interactive-discounts' ); ?></option>
                <option value="fixed_cart"><?php esc_html_e( 'Fixed Cart Discount', 'interactive-discounts' ); ?></option>
            </select>
            <input type="text" name="id_wheel_settings[segments][][value]" value="" placeholder="<?php esc_attr_e( 'Value (e.g., 10)', 'interactive-discounts' ); ?>" />
            <input type="text" name="id_wheel_settings[segments][][fillStyle]" value="#ffffff" class="color-picker" />
            <button type="button" class="button remove_segment_button"><?php esc_html_e( 'Remove', 'interactive-discounts' ); ?></button>
        </div>
        <?php
    }
}
