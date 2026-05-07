#include "searchable_bag.hpp"

class set
{
	private:
		searchable_bag& bag;
		// disabled (C++98 equivalent of = delete)
		set();
		set(const set& source);
		set& operator=(const set& source);
	public:
		set(searchable_bag& s_bag);
		bool has(int) const;
		void insert (int);
		void insert (int *, int);
		void print() const;
		void clear();

		const searchable_bag& get_bag();

		~set();

};
