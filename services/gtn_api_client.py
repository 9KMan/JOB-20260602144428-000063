"""
GTN API client for Order Search API integration.
"""
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from utils.config import config
from utils.logging import setup_logger
from models.gtn_order import Order, OrderSearchRequest, OrderSearchResponse

logger = setup_logger(__name__)


class GTNApiClient:
    """Client for GTN Trade API."""

    def __init__(self):
        self.base_url = config.get('gtn', 'api', 'base_url')
        self.api_key = config.get('gtn', 'api', 'api_key')
        self.order_search_endpoint = config.get('gtn', 'api', 'order_search_endpoint')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

    def search_orders(self, request: OrderSearchRequest) -> OrderSearchResponse:
        """
        Search orders using the GTN Order Search API.

        Args:
            request: OrderSearchRequest with search parameters

        Returns:
            OrderSearchResponse with matching orders

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}{self.order_search_endpoint}"

        params = {
            'page': str(request.page),
            'page_size': str(request.page_size)
        }

        if request.start_date:
            params['start_date'] = request.start_date.isoformat()
        if request.end_date:
            params['end_date'] = request.end_date.isoformat()
        if request.customer_id:
            params['customer_id'] = request.customer_id
        if request.status:
            params['status'] = request.status

        logger.info(f"Searching orders: {params}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            orders = [Order(**order_data) for order_data in data.get('orders', [])]

            return OrderSearchResponse(
                orders=orders,
                total_count=data.get('total_count', 0),
                page=data.get('page', request.page),
                page_size=data.get('page_size', request.page_size),
                has_more=data.get('has_more', False)
            )

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def fetch_orders_batch(
        self,
        start_date: datetime,
        end_date: datetime,
        batch_size: int = 100
    ) -> List[Order]:
        """
        Fetch all orders in batches between dates.

        Args:
            start_date: Start of date range
            end_date: End of date range
            batch_size: Number of orders per page

        Returns:
            List of all orders found
        """
        all_orders = []
        page = 1

        while True:
            request = OrderSearchRequest(
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=batch_size
            )

            response = self.search_orders(request)
            all_orders.extend(response.orders)

            logger.info(f"Fetched page {page}, {len(response.orders)} orders, "
                       f"total so far: {len(all_orders)}")

            if not response.has_more:
                break

            page += 1

            # Safety limit
            if page > 100:
                logger.warning("Reached page limit, stopping")
                break

        return all_orders

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """
        Get a single order by ID.

        Args:
            order_id: Order identifier

        Returns:
            Order if found, None otherwise
        """
        url = f"{self.base_url}/v1/orders/{order_id}"

        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return Order(**response.json())
        except requests.RequestException as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            return None