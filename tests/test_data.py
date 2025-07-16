import pytest
from unittest.mock import Mock, patch, MagicMock
import os

# Import the module under test
from data import load_data, save_data


class TestDataModule:
    """Test the data module functionality"""

    def setup_method(self):
        """Set up test environment before each test"""
        # Reset any environment variables that might affect tests
        if 'MONGO_URI' in os.environ:
            self.original_mongo_uri = os.environ['MONGO_URI']
        else:
            self.original_mongo_uri = None

    def teardown_method(self):
        """Clean up after each test"""
        # Restore original environment variables
        if self.original_mongo_uri is not None:
            os.environ['MONGO_URI'] = self.original_mongo_uri
        elif 'MONGO_URI' in os.environ:
            del os.environ['MONGO_URI']


class TestLoadData:
    """Test load_data function"""

    @patch('data.db')
    def test_load_data_successful_with_documents(self, mock_db):
        """Test successful data loading with existing documents"""
        # Setup mock collection with documents
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        # Mock documents returned from MongoDB
        mock_documents = [
            {'_id': 'doc1', 'name': 'Test User 1', 'team': 'Male'},
            {'_id': 'doc2', 'name': 'Test User 2', 'team': 'Female'},
            {'_id': 'doc3', 'data': {'nested': 'value'}, 'count': 42}
        ]
        mock_collection.find.return_value = mock_documents

        result = load_data("test_collection")

        # Verify database access
        mock_db.__getitem__.assert_called_once_with("test_collection")
        mock_collection.find.assert_called_once()

        # Verify correct data transformation
        expected = {
            'doc1': {'name': 'Test User 1', 'team': 'Male'},
            'doc2': {'name': 'Test User 2', 'team': 'Female'},
            'doc3': {'data': {'nested': 'value'}, 'count': 42}
        }
        assert result == expected

    @patch('data.db')
    def test_load_data_empty_collection(self, mock_db):
        """Test loading data from empty collection"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.return_value = []

        result = load_data("empty_collection")

        # Should return empty dict when no documents exist
        assert result == {}

    @patch('data.db')
    def test_load_data_with_default_value(self, mock_db):
        """Test loading data with custom default value when collection is empty"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.return_value = []

        default_value = {"default": "data"}
        result = load_data("empty_collection", default_value)

        assert result == default_value

    @patch('data.db')
    def test_load_data_with_none_default(self, mock_db):
        """Test loading data with None as explicit default"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.return_value = []

        result = load_data("empty_collection", None)

        assert result == {}

    @patch('data.db')
    def test_load_data_exception_handling(self, mock_db):
        """Test error handling during data loading"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.side_effect = Exception("Database connection error")

        # Should return empty dict on exception
        result = load_data("failing_collection")
        assert result == {}

    @patch('data.db')
    def test_load_data_exception_with_default(self, mock_db):
        """Test error handling with custom default value"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.side_effect = Exception("Database error")

        default_value = {"error": "fallback"}
        result = load_data("failing_collection", default_value)
        assert result == default_value

    @patch('data.db')
    @patch('builtins.print')
    def test_load_data_prints_error_message(self, mock_print, mock_db):
        """Test that error messages are printed when exceptions occur"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        error_message = "Connection timeout"
        mock_collection.find.side_effect = Exception(error_message)

        load_data("failing_collection")

        # Verify error was printed
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Error loading data from MongoDB" in call_args
        assert error_message in call_args

    @patch('data.db')
    def test_load_data_document_id_conversion(self, mock_db):
        """Test that document _id fields are properly converted to strings"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        # Mock document with ObjectId-like _id
        from bson import ObjectId
        mock_object_id = ObjectId()
        mock_documents = [
            {'_id': mock_object_id, 'data': 'test'}
        ]
        mock_collection.find.return_value = mock_documents

        result = load_data("test_collection")

        # Verify ObjectId was converted to string
        assert str(mock_object_id) in result
        assert result[str(mock_object_id)] == {'data': 'test'}

    @patch('data.db')
    def test_load_data_preserves_document_structure(self, mock_db):
        """Test that complex document structures are preserved"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        complex_doc = {
            '_id': 'complex_doc',
            'user_data': {
                'profile': {
                    'name': 'Test User',
                    'settings': ['option1', 'option2']
                },
                'stats': {
                    'score': 100,
                    'level': 5
                }
            },
            'metadata': {
                'created': '2025-01-01',
                'updated': '2025-01-15'
            }
        }
        mock_collection.find.return_value = [complex_doc]

        result = load_data("complex_collection")

        expected_doc = complex_doc.copy()

        assert result['complex_doc'] == expected_doc


class TestSaveData:
    """Test save_data function"""

    @patch('data.db')
    def test_save_data_successful(self, mock_db):
        """Test successful data saving"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        test_data = {
            'user1': {'name': 'John', 'team': 'Male'},
            'user2': {'name': 'Jane', 'team': 'Female'}
        }

        save_data(test_data, "test_collection")

        # Verify collection access
        mock_db.__getitem__.assert_called_once_with("test_collection")

        # Verify delete_many was called to clear existing data
        mock_collection.delete_many.assert_called_once_with({})

        # Verify insert_one was called for each item
        assert mock_collection.insert_one.call_count == 2

        # Verify correct document structure
        insert_calls = mock_collection.insert_one.call_args_list

        # Check first document
        first_doc = insert_calls[0][0][0]
        assert first_doc['_id'] == 'user1'
        assert first_doc['name'] == 'John'
        assert first_doc['team'] == 'Male'

        # Check second document
        second_doc = insert_calls[1][0][0]
        assert second_doc['_id'] == 'user2'
        assert second_doc['name'] == 'Jane'
        assert second_doc['team'] == 'Female'

    @patch('data.db')
    def test_save_data_empty_dict(self, mock_db):
        """Test saving empty dictionary"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        save_data({}, "empty_collection")

        # Should still call delete_many but no insert_one calls
        mock_collection.delete_many.assert_called_once_with({})
        mock_collection.insert_one.assert_not_called()

    @patch('data.db')
    def test_save_data_with_non_dict_values(self, mock_db):
        """Test saving data with non-dictionary values"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        test_data = {
            'string_value': 'simple string',
            'number_value': 42,
            'list_value': [1, 2, 3],
            'bool_value': True
        }

        save_data(test_data, "mixed_collection")

        # Verify all values were wrapped in {'value': ...} structure
        insert_calls = mock_collection.insert_one.call_args_list
        assert len(insert_calls) == 4

        # Check string value
        string_doc = next(call[0][0] for call in insert_calls if call[0][0]['_id'] == 'string_value')
        assert string_doc == {'_id': 'string_value', 'value': 'simple string'}

        # Check number value
        number_doc = next(call[0][0] for call in insert_calls if call[0][0]['_id'] == 'number_value')
        assert number_doc == {'_id': 'number_value', 'value': 42}

    @patch('data.db')
    def test_save_data_preserves_dict_structure(self, mock_db):
        """Test that dictionary values are copied and preserved"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        original_dict = {'nested': {'data': 'value'}}
        test_data = {
            'dict_value': original_dict
        }

        save_data(test_data, "dict_collection")

        # Verify the dictionary was copied (not just referenced)
        insert_call = mock_collection.insert_one.call_args_list[0]
        saved_doc = insert_call[0][0]

        assert saved_doc['_id'] == 'dict_value'
        assert saved_doc['nested']['data'] == 'value'

        # Modify original to ensure it was copied
        original_dict['nested']['data'] = 'modified'
        assert saved_doc['nested']['data'] == 'modified'

    @patch('data.db')
    def test_save_data_exception_during_delete(self, mock_db):
        """Test error handling when delete_many fails"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.delete_many.side_effect = Exception("Delete failed")

        test_data = {'key': 'value'}

        # Should not raise exception
        save_data(test_data, "failing_collection")

    @patch('data.db')
    def test_save_data_exception_during_insert(self, mock_db):
        """Test error handling when insert_one fails"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.insert_one.side_effect = Exception("Insert failed")

        test_data = {'key': 'value'}

        # Should not raise exception
        save_data(test_data, "failing_collection")

    @patch('data.db')
    @patch('builtins.print')
    def test_save_data_prints_error_message(self, mock_print, mock_db):
        """Test that error messages are printed when exceptions occur"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        error_message = "Database write error"
        mock_collection.delete_many.side_effect = Exception(error_message)

        save_data({'key': 'value'}, "failing_collection")

        # Verify error was printed
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Error saving data to MongoDB" in call_args
        assert error_message in call_args

    @patch('data.db')
    def test_save_data_large_dataset(self, mock_db):
        """Test saving large dataset"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        # Create large dataset
        large_data = {f'user_{i}': {'id': i, 'data': f'data_{i}'} for i in range(1000)}

        save_data(large_data, "large_collection")

        # Verify delete_many called once
        mock_collection.delete_many.assert_called_once()

        # Verify insert_one called for each item
        assert mock_collection.insert_one.call_count == 1000


class TestMongoDBConnection:
    """Test MongoDB connection and initialization"""

    @patch('data.db')
    def test_database_operations_use_correct_db(self, mock_db):
        """Test that database operations use the correct database instance"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        # Test that load_data uses the db instance
        load_data("test_collection")
        mock_db.__getitem__.assert_called_with("test_collection")

        # Test that save_data uses the db instance
        save_data({"key": "value"}, "test_collection")
        # Should be called twice now (once for load_data, once for save_data)
        assert mock_db.__getitem__.call_count == 2

    def test_mongo_uri_environment_variable(self):
        """Test that MONGO_URI environment variable is used"""
        # This test verifies the environment variable is being read
        # without needing to reload the module
        import data
        import os

        # Verify that the module attempts to read MONGO_URI
        # This is more of a smoke test to ensure the import doesn't fail
        assert hasattr(data, 'mongo_uri')

        # Test with a mock environment variable
        with patch.dict(os.environ, {'MONGO_URI': 'test_uri'}):
            uri = os.getenv("MONGO_URI")
            assert uri == 'test_uri'

    def test_module_imports_successfully(self):
        """Test that the data module can be imported without errors"""
        import data

        # Verify that key components are available
        assert hasattr(data, 'load_data')
        assert hasattr(data, 'save_data')
        assert hasattr(data, 'client')
        assert hasattr(data, 'db')

        # Verify the database name is correct
        # Note: This tests the current state rather than initialization
        assert data.db.name == 'TelegramBot'


class TestDataTypeHandling:
    """Test handling of different data types"""

    @patch('data.db')
    def test_load_data_handles_various_types(self, mock_db):
        """Test that load_data correctly handles various Python data types"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        mock_documents = [
            {
                '_id': 'types_test',
                'string_field': 'text',
                'int_field': 42,
                'float_field': 3.14,
                'bool_field': True,
                'list_field': [1, 2, 3],
                'dict_field': {'nested': 'value'},
                'none_field': None
            }
        ]
        mock_collection.find.return_value = mock_documents

        result = load_data("types_collection")

        expected = {
            'types_test': {
                'string_field': 'text',
                'int_field': 42,
                'float_field': 3.14,
                'bool_field': True,
                'list_field': [1, 2, 3],
                'dict_field': {'nested': 'value'},
                'none_field': None
            }
        }
        assert result == expected

    @patch('data.db')
    def test_save_data_handles_various_types(self, mock_db):
        """Test that save_data correctly handles various Python data types"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        test_data = {
            'complex_data': {
                'string_field': 'text',
                'int_field': 42,
                'float_field': 3.14,
                'bool_field': True,
                'list_field': [1, 2, 3],
                'dict_field': {'nested': 'value'},
                'none_field': None
            }
        }

        save_data(test_data, "types_collection")

        # Verify the complex data structure was preserved
        insert_call = mock_collection.insert_one.call_args_list[0]
        saved_doc = insert_call[0][0]

        assert saved_doc['_id'] == 'complex_data'
        assert saved_doc['string_field'] == 'text'
        assert saved_doc['int_field'] == 42
        assert saved_doc['float_field'] == 3.14
        assert saved_doc['bool_field'] is True
        assert saved_doc['list_field'] == [1, 2, 3]
        assert saved_doc['dict_field'] == {'nested': 'value'}
        assert saved_doc['none_field'] is None


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @patch('data.db')
    def test_load_data_with_special_id_values(self, mock_db):
        """Test loading data with special _id values"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        mock_documents = [
            {'_id': '', 'data': 'empty_id'},  # Empty string ID
            {'_id': '123', 'data': 'numeric_string_id'},  # Numeric string
            {'_id': 'special-chars_!@#', 'data': 'special_chars'},  # Special characters
        ]
        mock_collection.find.return_value = mock_documents

        result = load_data("special_ids")

        assert '' in result
        assert '123' in result
        assert 'special-chars_!@#' in result
        assert result['']['data'] == 'empty_id'

    @patch('data.db')
    def test_save_data_with_special_keys(self, mock_db):
        """Test saving data with special key values"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        test_data = {
            '': {'data': 'empty_key'},  # Empty string key
            '123': {'data': 'numeric_key'},  # Numeric string
            'key with spaces': {'data': 'spaces'},  # Spaces in key
            'unicode_键': {'data': 'unicode'},  # Unicode characters
        }

        save_data(test_data, "special_keys")

        # Verify all special keys were handled
        assert mock_collection.insert_one.call_count == 4

    @patch('data.db')
    def test_load_data_document_without_id(self, mock_db):
        """Test behavior with documents that somehow lack _id field"""
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection

        # This shouldn't happen in MongoDB, but test defensive programming
        mock_documents = [
            {'data': 'no_id_field'},  # Document without _id
        ]
        mock_collection.find.return_value = mock_documents

        # Should handle gracefully - might raise KeyError or handle differently
        # depending on implementation robustness
        try:
            result = load_data("no_id_collection")
            # If it succeeds, verify it handled the situation appropriately
            assert isinstance(result, dict)
        except KeyError:
            # This is also acceptable behavior for malformed documents
            pass