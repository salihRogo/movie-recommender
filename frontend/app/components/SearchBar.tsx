import { Form } from "@remix-run/react";

const SearchBar = () => {
  return (
    <Form method="post" className="w-full max-w-xl mx-auto">
      <input type="hidden" name="intent" value="search" />
      <input
        type="text"
        name="query"
        placeholder="Search for a movie..."
        className="w-full px-4 py-2 text-gray-900 bg-white border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </Form>
  );
};

export default SearchBar;
