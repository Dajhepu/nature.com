<?php
if ( ! class_exists( 'WP_List_Table' ) ) {
    require_once( ABSPATH . 'wp-admin/includes/class-wp-list-table.php' );
}

class Interactive_Discounts_Emails_List_Table extends WP_List_Table {

    public function __construct() {
        parent::__construct( [
            'singular' => __( 'Email', 'interactive-discounts' ),
            'plural'   => __( 'Emails', 'interactive-discounts' ),
            'ajax'     => false
        ] );
    }

    public static function get_emails( $per_page = 5, $page_number = 1 ) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'id_collected_emails';
        $sql = "SELECT * FROM {$table_name}";
        if ( ! empty( $_REQUEST['orderby'] ) ) {
            $sql .= ' ORDER BY ' . esc_sql( $_REQUEST['orderby'] );
            $sql .= ! empty( $_REQUEST['order'] ) ? ' ' . esc_sql( $_REQUEST['order'] ) : ' ASC';
        }
        $sql .= " LIMIT $per_page";
        $sql .= ' OFFSET ' . ( $page_number - 1 ) * $per_page;
        $result = $wpdb->get_results( $sql, 'ARRAY_A' );
        return $result;
    }

    public static function record_count() {
        global $wpdb;
        $table_name = $wpdb->prefix . 'id_collected_emails';
        $sql = "SELECT COUNT(*) FROM {$table_name}";
        return $wpdb->get_var( $sql );
    }

    public function no_items() {
        _e( 'No emails collected yet.', 'interactive-discounts' );
    }

    function column_default( $item, $column_name ) {
        switch ( $column_name ) {
            case 'email':
            case 'time':
                return $item[ $column_name ];
            default:
                return print_r( $item, true ); //Show the whole array for troubleshooting purposes
        }
    }

    function get_columns() {
        $columns = [
            'email' => __( 'Email', 'interactive-discounts' ),
            'time'  => __( 'Time', 'interactive-discounts' ),
        ];
        return $columns;
    }

    public function get_sortable_columns() {
        $sortable_columns = array(
            'email' => array( 'email', true ),
            'time' => array( 'time', false )
        );
        return $sortable_columns;
    }

    public function prepare_items() {
        $this->_column_headers = $this->get_column_info();
        $per_page     = $this->get_items_per_page( 'emails_per_page', 5 );
        $current_page = $this->get_pagenum();
        $total_items  = self::record_count();
        $this->set_pagination_args( [
            'total_items' => $total_items,
            'per_page'    => $per_page
        ] );
        $this->items = self::get_emails( $per_page, $current_page );
    }
}
