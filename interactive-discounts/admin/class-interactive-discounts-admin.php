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
        add_menu_page(
            __( 'Interactive Discounts Settings', 'interactive-discounts' ),
            __( 'Discount Games', 'interactive-discounts' ),
            'manage_options',
            'interactive-discounts-settings',
            array( $this, 'create_admin_page' ),
            'dashicons-games'
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

    public function page_init() {
        register_setting('id_wheel_option_group', 'id_wheel_settings', array( $this, 'sanitize' ));
        add_settings_section('setting_section_id', __( 'Wheel of Fortune Settings', 'interactive-discounts' ), array( $this, 'print_section_info' ), 'interactive-discounts-admin');
        add_settings_field('enable_wheel', __( 'Enable Wheel', 'interactive-discounts' ), array( $this, 'enable_wheel_callback' ), 'interactive-discounts-admin', 'setting_section_id');
        add_settings_field('segments', __( 'Wheel Segments', 'interactive-discounts' ), array( $this, 'segments_callback' ), 'interactive-discounts-admin', 'setting_section_id');
    }

    public function sanitize( $input ) {
        $new_input = array();
        if( isset( $input['enable_wheel'] ) ) $new_input['enable_wheel'] = absint( $input['enable_wheel'] );
        if( isset( $input['segments'] ) ) {
             $new_input['segments'] = array_map( function($segment) {
                return [
                    'text'      => sanitize_text_field($segment['text']),
                    'type'      => sanitize_text_field($segment['type']),
                    'value'     => sanitize_text_field($segment['value']),
                    'fillStyle' => sanitize_hex_color($segment['fillStyle']),
                ];
             }, $input['segments']);
        }
        return $new_input;
    }

    public function print_section_info() {
        esc_html_e( 'Configure the Wheel of Fortune below:', 'interactive-discounts' );
    }

    public function enable_wheel_callback() {
        printf(
            '<input type="checkbox" id="enable_wheel" name="id_wheel_settings[enable_wheel]" value="1" %s /> <label for="enable_wheel">%s</label>',
            isset( $this->options['enable_wheel'] ) && $this->options['enable_wheel'] == 1 ? 'checked' : '',
            esc_html__( 'Check to enable the Wheel of Fortune popup on your site.', 'interactive-discounts' )
        );
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
